from pathlib import Path

import pypsa

from andromede.input_converter.src.logger import Logger
from tests.pypsa_converter.test_advanced_pypsa_cases import (
    load_pypsa_study,
    replace_lines_by_links,
)


def replace_lines_by_links(network):
    """
    Replace lines in a PyPSA network with equivalent links.

    This function converts transmission lines to links, which allows for more
    flexible modeling of power flow constraints. Each line is replaced with
    two links (one for each direction) to maintain bidirectional flow capability.

    Args:
        network (pypsa.Network): The PyPSA network to modify

    Returns:
        pypsa.Network: The modified network with lines replaced by links
    """

    # Create a copy of the lines DataFrame to iterate over
    lines = network.lines.copy()

    # For each line, create two links (one for each direction)
    for idx, line in lines.iterrows():
        # Create a unique name for the links
        link_name_forward = f"{idx} link forward"
        link_name_backward = f"{idx} link backward"

        # Get line parameters
        bus0 = line["bus0"]
        bus1 = line["bus1"]
        s_nom = line["s_nom"]
        s_max_pu = line["s_max_pu"]

        # Add forward link
        network.add(
            "Link",
            link_name_forward + bus0 + bus1,
            bus0=bus0,
            bus1=bus1,
            p_min_pu=-s_max_pu,
            p_max_pu=s_max_pu,
            p_nom=s_nom,  # Use line capacity as link capacity
            efficiency=1.0,
        )

    network.remove("Line", lines.index)

    return network


def run_line_to_link_comparison(file_name, load_scaling) -> None:

    logger = Logger(__name__, Path(""))

    # Load the PyPSA study
    logger.info("Loading PyPSA study...")
    pypsa_network = load_pypsa_study(file_name, load_scaling)
    logger.info(
        f"Loaded PyPSA network with {len(pypsa_network.buses)} buses and {len(pypsa_network.generators)} generators"
    )
    # Optimize PyPSA network
    logger.info("Solving PyPSA network before line to link...")
    pypsa_network.optimize(solver_name="mosek")
    # pypsa_network.model.to_file("pypsa.lp", explicit_coordinate_names=True)
    objective_lines = pypsa_network.objective
    logger.info(f"PyPSA objective value: {objective_lines}")
    pypsa_network_links = load_pypsa_study(file_name, load_scaling)
    pypsa_network_links = replace_lines_by_links(pypsa_network_links)
    logger.info("Solving PyPSA network after line to link...")
    pypsa_network_links.optimize(solver_name="mosek")
    objective_links = pypsa_network_links.objective
    logger.info(f"PyPSA objective value with lines: {objective_lines}")
    logger.info(f"PyPSA objective value with links: {objective_links}")
    rel_diff = abs(objective_lines - objective_links) / objective_lines * 100.0
    logger.info(f"Relative difference: {rel_diff:.3f} %")

    return rel_diff


def test_radial_network():

    rel_diff = run_line_to_link_comparison("base_s_4_elec.nc", 0.8)
    assert rel_diff < 0.01


def test_meshed_network():

    rel_diff = run_line_to_link_comparison("base_s_10_elec.nc", 0.6)
    assert rel_diff > 0.01
