"""Builds the PDF report from the summary and the figures. Every number is read from the output files."""

import json
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from cleaner import Strategy
from simulation import SimConfig

STYLES = getSampleStyleSheet()
BODY = STYLES["BodyText"]
H1 = STYLES["Heading1"]
H2 = STYLES["Heading2"]
SMALL = STYLES["BodyText"].clone("small", fontSize=8, leading=10)
PLACEHOLDER = "[to be added]"


@dataclass(frozen=True)
class ReportInputs:
    output: Path
    base: SimConfig
    agent_counts: list[int]
    scaling_agents: int
    seeds: int
    video_urls: dict[str, str]
    code_url: str
    author: str
    course: str
    assignment: str


def fmt(value, digits: int = 0) -> str:
    return "did not finish" if value is None else f"{value:.{digits}f}"


def percent(value: float) -> str:
    return f"{value:.0f}%"


def table(rows: list[list[str]], widths: list[float] | None = None) -> Table:
    grid = Table(rows, repeatRows=1, colWidths=widths)
    grid.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return grid


def design_matrix(inputs: ReportInputs) -> Table:
    b = inputs.base
    rows = [
        ["Factor", "Levels used"],
        ["Room (M x N grid)", f"{b.rows} x {b.cols} ({b.rows * b.cols} cells)"],
        ["Dirty grid cells", f"{b.dirty_fraction:.0%} of the cells, placed at random for every seed"],
        ["Number of agents", "1 (Simulation 1); " + ", ".join(map(str, inputs.agent_counts))
         + f" (Simulation 2); {inputs.scaling_agents} for the strategy comparison and the videos"],
        ["Trajectory type", ", ".join(s.value.replace("_", " ") for s in Strategy)],
        ["Maximum simulation time", f"{b.max_steps} ticks"],
        ["Start cell (Simulation 2)", f"cell {b.start}, the same for every agent"],
        ["Repetitions", f"{inputs.seeds} random seeds per setting"],
    ]
    return table(rows, widths=[1.9 * inch, 4.9 * inch])


def results_table(summary: dict, names: list[str]) -> Table:
    rows = [["Experiment", "Finished", "Time (ticks)", "Cleaned", "Visited", "Moves / agent", "Distance (m)"]]
    for name in names:
        s = summary[name]
        rows.append([
            name,
            percent(s["finished_rate_pct"]),
            fmt(s["time_to_clean_mean"], 1),
            f"{s['cleaned_pct_mean']:.1f}%",
            f"{s['visited_pct_mean']:.1f}%",
            f"{s['mean_moves_per_agent']:.1f}",
            f"{s['distance_m_mean']:.1f}",
        ])
    return table(rows)


def _scaling_table(s: dict, names: list[str], inputs: ReportInputs) -> Table:
    rows = [["Agents", "P(all dirt cleaned)", "Time (ticks)", "Time std", "Visited", "Moves / agent", "Total moves"]]
    for name in names:
        x = s[name]
        successes = round(x["finished_rate_pct"] * inputs.seeds / 100)
        rows.append([
            str(x["n_agents"]),
            f"{successes / inputs.seeds:.2f} ({successes}/{inputs.seeds})",
            fmt(x["time_to_clean_mean"], 1),
            fmt(x["time_to_clean_std"], 1),
            f"{x['visited_pct_mean']:.1f}%",
            f"{x['mean_moves_per_agent']:.1f}",
            f"{x['total_moves_mean']:.1f}",
        ])
    return table(rows)


def _strategy_paragraphs(s: dict, n: int) -> list[str]:
    parts = []
    for strategy in Strategy:
        if strategy is Strategy.LOCAL_SEARCH:
            continue
        one = s[f"sim1-{strategy.value}"]
        many = s[f"sim2-{strategy.value}-n{n}"]
        label = strategy.value.replace("_", " ").capitalize()
        parts.append(
            f"<b>{label}.</b> With one agent it cleaned {one['cleaned_pct_mean']:.1f}% of the dirt on average and "
            f"finished in {percent(one['finished_rate_pct'])} of runs (time {fmt(one['time_to_clean_mean'], 1)} ticks). "
            f"With {n} agents it cleaned {many['cleaned_pct_mean']:.1f}% and finished in "
            f"{percent(many['finished_rate_pct'])} of runs (time {fmt(many['time_to_clean_mean'], 1)} ticks)."
        )
    return parts


def build_story(summary: dict, inputs: ReportInputs) -> list:
    s = summary
    n = inputs.scaling_agents
    counts = inputs.agent_counts
    b = inputs.base
    sim1 = s["sim1-local_search"]
    sim2_n = s[f"sim2-local_search-n{n}"]
    scaling = [sim1] + [s[f"sim2-local_search-n{c}"] for c in counts]
    scaling_names = ["sim1-local_search"] + [f"sim2-local_search-n{c}" for c in counts]
    times = [fmt(x["time_to_clean_mean"], 1) for x in scaling]
    moves = [f"{x['mean_moves_per_agent']:.1f}" for x in scaling]
    cut = 100 * (1 - sim2_n["time_to_clean_mean"] / sim1["time_to_clean_mean"])
    video_lines = [
        Paragraph(f"{strategy.value.replace('_', ' ').capitalize()}: "
                  f"{inputs.video_urls.get(strategy.value, PLACEHOLDER)}", BODY)
        for strategy in Strategy
    ]

    return [
        Spacer(1, 1.2 * inch),
        Paragraph("Multi-Agent Room Cleaning: Simulation Report", H1),
        Spacer(1, 12),
        Paragraph(f"Course: {inputs.course}", BODY),
        Paragraph(f"Assignment: {inputs.assignment}", BODY),
        Paragraph(f"Author: {inputs.author}", BODY),
        Spacer(1, 24),
        Paragraph(f"Code: {inputs.code_url}", BODY),
        Paragraph("Videos (Google Drive), one per trajectory type, one agent next to four agents:", BODY),
        *video_lines,
        PageBreak(),

        Paragraph("1. Introduction", H2),
        Paragraph(
            f"We simulated agents that clean a {b.rows} x {b.cols} room in which "
            f"{b.dirty_fraction:.0%} of the cells are dirty, placed at random. Two setups were studied. In "
            "<b>Simulation 1</b> one agent cleans the room. In <b>Simulation 2</b> several agents start at the same "
            "cell. We measured the time needed to clean the dirt, the share of cells visited, the share of dirt "
            "cleaned, the moves made by each agent, and how adding agents changes these numbers.",
            BODY,
        ),

        Paragraph("2. Methods", H2),
        Paragraph(
            "<b>2.1 The problem and the three planning methods.</b> The objective of the agents is to clean as much "
            "dirt as possible before the time limit. Each agent chooses where to go with one of three planning "
            "methods. <i>Local search</i> plans greedily: it walks the shortest path to the nearest dirty cell that no "
            "other agent is already heading for. <i>Zigzag</i> follows a fixed plan: a route that sweeps the rows left "
            "to right and then right to left, closed into a loop. <i>Random</i> plans probabilistically: on every tick "
            "it moves to a neighbour drawn from row <i>P</i> of the probability matrix.",
            BODY,
        ),
        Paragraph(
            "<b>2.2 The environment.</b> The room is an M x N grid, here "
            f"{b.rows} x {b.cols}. Cells are numbered row by row, so cell = row x N + column. Each run places "
            f"round({b.dirty_fraction:.2f} x cells) dirty cells at random. Time runs in ticks with a limit of "
            f"{b.max_steps}. In each tick an agent either cleans the cell it stands on (costing one tick and no move) "
            "or moves to a neighbour (one tick and one move). Three matrices describe the room, as in the course "
            "notebook (Figure 0): <i>S</i> marks which cells are neighbours (8 directions, diagonals included); "
            "<i>D</i> holds the distance in metres between any two cells, 0.3 m per tile; and <i>P</i> is <i>S</i> "
            "with each row divided by its sum, so a random agent picks each neighbour with equal probability.",
            BODY,
        ),
        Paragraph(
            "<b>2.3 Agents, objectives, architecture and interaction.</b> Each agent keeps its cell, the list of "
            "cells it has entered (its route), and its move count. The room keeps the set of dirty cells. Agents act "
            "one after another in the same order every tick. In Simulation 2 they also share a claim list, so two "
            "agents do not head for the same dirty cell. The architecture has five parts: the grid (matrices S, D, P "
            "and the shortest paths), the cleaner (one agent and its strategy), the simulation (one run and its "
            "metrics), the batch and video code, and the command-line interface with two subcommands. The run writes "
            "<i>Nodes.csv</i> (each cell, its position and its dirt) and <i>Routes.csv</i> (each agent and the cells "
            "it entered, in order), which the Flask app <i>Main.py</i> reads.",
            BODY,
        ),
        Image(str(inputs.output / "matrices.png"), width=6.2 * inch, height=2.1 * inch),
        Paragraph("Figure 0. The matrices S (allowed moves), D (distances in metres) and P (transition probabilities) "
                  f"for the {b.rows} x {b.cols} grid.", SMALL),
        Paragraph("<b>2.4 Design matrix.</b>", BODY),
        design_matrix(inputs),
        PageBreak(),

        Paragraph("3. Results", H2),
        Paragraph(
            f"<b>Simulation 1 (one agent, local search).</b> The dirt was fully cleaned after "
            f"{fmt(sim1['time_to_clean_mean'], 1)} ticks on average. The agent visited {sim1['visited_pct_mean']:.1f}% of "
            f"the cells, made {sim1['mean_moves_per_agent']:.1f} moves and walked {sim1['distance_m_mean']:.1f} m.",
            BODY,
        ),
        Paragraph(
            f"<b>Simulation 2 (local search).</b> With {n} agents the dirt was cleaned after "
            f"{fmt(sim2_n['time_to_clean_mean'], 1)} ticks on average, and finished in "
            f"{percent(sim2_n['finished_rate_pct'])} of runs. The agents visited {sim2_n['visited_pct_mean']:.1f}% "
            f"of the cells.",
            BODY,
        ),
        *[Paragraph(text, BODY) for text in _strategy_paragraphs(s, n)],
        Spacer(1, 6),
        results_table(summary, list(summary.keys())),
        Paragraph(f"Table 1. Averages over {inputs.seeds} seeds. Time is averaged over finished runs only.", SMALL),
        Spacer(1, 8),
        Image(str(inputs.output / "strategies.png"), width=6.8 * inch, height=2.55 * inch),
        Paragraph(f"Figure 1. The three trajectory types with one agent (Simulation 1) and {n} agents (Simulation 2).",
                  SMALL),
        PageBreak(),

        Paragraph("4. Effect of adding agents", H2),
        Paragraph(
            f"We kept local search and changed only the number of agents. Time to clean went from {times[0]} ticks "
            f"with one agent to {times[1]} with {counts[0]}, {times[2]} with {counts[1]}, {times[3]} with {counts[2]}, "
            f"and {times[4]} with {counts[3]}. The moves per agent went from {moves[0]} to {moves[4]}. Going from one "
            f"agent to {n} agents cut the time by about {cut:.0f}%. The share of cells visited is a different measure: "
            "it reports how much of the grid the agents walked on, not how fast the dirt was cleaned.",
            BODY,
        ),
        Spacer(1, 6),
        _scaling_table(s, scaling_names, inputs),
        Paragraph("Table 2. Effect of the number of agents (local search). P(all dirt cleaned) is the share of seeds "
                  "in which every dirty cell was cleaned.", SMALL),
        Spacer(1, 8),
        Image(str(inputs.output / "agent_scaling.png"), width=6.8 * inch, height=2.1 * inch),
        Paragraph(f"Figure 2. Local search with 1 agent (Simulation 1) and with "
                  f"{', '.join(map(str, counts))} agents (Simulation 2).", SMALL),
        Spacer(1, 8),
        Paragraph("<b>Probability that all dirt is cleaned.</b> " + _probability_sentence(s, inputs.seeds),
                  BODY),
        PageBreak(),

        Paragraph("5. Recorded simulation data", H2),
        Paragraph(
            "The per-run measurements are in <i>output/runs.csv</i>, the settings of every experiment in "
            "<i>output/config.json</i>, and the aggregated numbers in <i>output/summary.json</i>. The room and the "
            "routes of the last simulation run are in <i>Nodes.csv</i> and <i>Routes.csv</i>. Three videos show one "
            f"run of each trajectory type with one agent next to {n} agents, on the same grid and dirt. They are "
            "<i>output/simulation-local_search.mp4</i>, <i>simulation-zigzag.mp4</i> and "
            "<i>simulation-random.mp4</i>, and are linked on the first page.",
            BODY,
        ),

        Paragraph("6. Conclusions", H2),
        Paragraph(_conclusions(s, n), BODY),
        Paragraph(
            "<b>Limitations.</b> The results are for one grid size and one dirt percentage. The agents move one cell "
            "per tick, and the claim list is the only coordination between agents. Local search and zigzag are "
            "deterministic for a given dirt pattern, so their probabilities reflect the dirt patterns sampled, not "
            "randomness in the strategy.",
            BODY,
        ),
    ]


def _probability_sentence(s: dict, seeds: int) -> str:
    parts = []
    for strategy in Strategy:
        successes = round(s[f"sim1-{strategy.value}"]["finished_rate_pct"] * seeds / 100)
        parts.append(f"{strategy.value.replace('_', ' ')} {successes / seeds:.2f} ({successes}/{seeds})")
    return (f"With one agent, over {seeds} seeds, the estimated probability that all dirt is cleaned within the "
            "time limit is " + ", ".join(parts) + ". The column P(all dirt cleaned) in Table 2 gives the same "
            "estimate for local search with each number of agents.")


def _conclusions(s: dict, n: int) -> str:
    local1 = s["sim1-local_search"]
    local_n = s[f"sim2-local_search-n{n}"]
    return (
        f"Local search cleaned the dirt with one agent in {fmt(local1['time_to_clean_mean'], 1)} ticks and with "
        f"{n} agents in {fmt(local_n['time_to_clean_mean'], 1)} ticks. Adding agents shortens the job, with a smaller "
        f"gain each time. Zigzag always finishes but takes longer, and random walk is the slowest and the costliest in "
        f"moves ({s['sim1-random']['mean_moves_per_agent']:.1f} moves per agent with one agent, against "
        f"{local1['mean_moves_per_agent']:.1f} for local search)."
    )


def build_report(inputs: ReportInputs, path: Path) -> None:
    summary = json.loads((inputs.output / "summary.json").read_text())
    doc = SimpleDocTemplate(str(path), pagesize=letter,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="Multi-Agent Room Cleaning: Simulation Report",
                            author=inputs.author)
    doc.build(build_story(summary, inputs))
