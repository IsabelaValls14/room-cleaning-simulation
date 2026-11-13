"""Builds the PDF report from output/summary.json and the chart images. Numbers are read, not typed in."""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUTPUT = Path(__file__).parent / "output"
REPORT = OUTPUT / "report.pdf"
VIDEO_URL = "https://drive.google.com/file/d/1rTucZkD9xcOqsQbjx_CtyDzfxDSlZOeA/view?usp=sharing"
CODE_URL = "[Code repository URL - to be added after publishing]"
AGENT_COUNTS = (1, 2, 4, 8, 16)

STYLES = getSampleStyleSheet()
BODY = STYLES["BodyText"]
H1 = STYLES["Heading1"]
H2 = STYLES["Heading2"]


def load_summary() -> dict:
    return json.loads((OUTPUT / "summary.json").read_text())


def fmt(value) -> str:
    return "did not finish" if value is None else f"{value:.0f}"


def results_table(summary: dict, names: list[str]) -> Table:
    header = ["Experiment", "Finished", "Time to clean (ticks)", "Cleaned", "Visited", "Moves / agent", "Recharges"]
    rows = [header]
    for name in names:
        s = summary[name]
        rows.append([
            name,
            f"{s['finished_rate_pct']:.0f}%",
            fmt(s["time_to_clean_mean"]),
            f"{s['cleaned_pct_mean']:.1f}%",
            f"{s['visited_pct_mean']:.1f}%",
            f"{s['mean_moves_per_agent']:.1f}",
            f"{s['recharges_mean']:.1f}",
        ])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def scaling_numbers(summary: dict) -> tuple[list[str], list[str]]:
    names = ["sim1-local_search"] + [f"sim2-local_search-n{n}" for n in AGENT_COUNTS[1:]]
    times = [fmt(summary[name]["time_to_clean_mean"]) for name in names]
    moves = [f"{summary[name]['mean_moves_per_agent']:.0f}" for name in names]
    return times, moves


def build_story(summary: dict) -> list:
    s1 = summary["sim1-local_search"]
    s2_4 = summary["sim2-local_search-n4"]
    s2_16 = summary["sim2-local_search-n16"]
    random_1 = summary["sim1-random"]
    random_4 = summary["sim2-random-n4"]
    zigzag_1 = summary["sim1-zigzag"]
    zigzag_4 = summary["sim2-zigzag-n4"]
    times, moves = scaling_numbers(summary)
    t_1 = summary["sim1-local_search"]["time_to_clean_mean"]
    t_4 = summary["sim2-local_search-n4"]["time_to_clean_mean"]
    t_8 = summary["sim2-local_search-n8"]["time_to_clean_mean"]
    t_16 = summary["sim2-local_search-n16"]["time_to_clean_mean"]
    cut_1_to_4 = 100 * (1 - t_4 / t_1)
    saved_8_to_16 = t_8 - t_16

    story = [
        Paragraph("Multi-Agent Room Cleaning: Simulation Report", H1),
        Paragraph(f"Video: {VIDEO_URL}<br/>Code: {CODE_URL}", BODY),
        Spacer(1, 10),
        Paragraph("1. Introduction", H2),
        Paragraph(
            "We built a small simulation of cleaning agents working in a room with dirt and obstacles. "
            "Each agent has a limited battery, so it has to go back and recharge. We ran two setups. "
            "In Simulation 1 a single agent cleans the room. In Simulation 2 several agents start at random "
            "cells and can recharge at any agent's starting cell. We wanted to see how fast the room gets clean, "
            "how much of it the agents actually visit, and what happens when we add more agents.",
            BODY,
        ),
        Paragraph("2. Methods", H2),
        Paragraph("<b>The problem.</b> Clean as much dirt as possible before the time runs out. The agents "
                  "have a battery that limits how many cells they can enter, and some cells are locked, so "
                  "nobody can step on them. The agent that decides where to go is the trajectory strategy: "
                  "local search, zigzag, or random walk.", BODY),
        Paragraph("<b>The environment.</b> The room is a 20 x 20 grid. For each run, 30% of the cells start "
                  "dirty and 10% are locked, placed at random. If the locked cells split the room into pieces, "
                  "we draw again, so every free cell can be reached. Time runs in ticks, with a limit of 1000. "
                  "In each tick an agent does one thing: it recharges, cleans the cell it is standing on, moves "
                  "one cell, or waits. Cleaning costs a tick but no battery. Each move costs one tick and one "
                  "battery unit. Each battery holds 250 moves.", BODY),
        Paragraph("<b>What the agents do.</b> Each agent keeps its position, its battery, the set of cells it has "
                  "entered, and a move counter. The room keeps track of which cells are still dirty. In Simulation 2 "
                  "the agents also share a list of dirt cells that someone is already heading for, so two agents "
                  "don't walk to the same spot. An agent heads back to the nearest starting cell once, after it "
                  "reaches that cell, it would have 5% of its battery left (13 moves). There it recharges to full. "
                  "The agents take turns in the same order every tick.", BODY),
        Paragraph("<b>The three strategies.</b> <i>Local search</i> walks the shortest path to the nearest dirty cell "
                  "that no other agent is already going for. <i>Zigzag</i> walks a fixed back-and-forth route "
                  "over the whole room, starting from the agent's own cell. <i>Random</i> picks one free neighboring "
                  "cell at random on every tick.", BODY),
        Paragraph("<b>What we measured.</b> The tick when the last dirty cell is cleaned, the share of free cells "
                  "the agents entered, the share of dirty cells that got cleaned, the moves each agent made, and "
                  "how many times agents recharged. Every setup was run with 30 random seeds, and we report averages "
                  "(with standard deviations where it matters).", BODY),
        Paragraph("3. Results", H2),
        Paragraph(
            f"<b>Simulation 1 (one agent, local search).</b> The room was fully cleaned after "
            f"{fmt(s1['time_to_clean_mean'])} ticks on average (std {s1['time_to_clean_std']}). The agent "
            f"entered {s1['visited_pct_mean']:.0f}% of the free cells and made {s1['mean_moves_per_agent']:.0f} moves.",
            BODY,
        ),
        Paragraph(
            f"<b>Simulation 2 (local search).</b> With 4 agents the room was clean after "
            f"{fmt(s2_4['time_to_clean_mean'])} ticks. With 16 agents it took {fmt(s2_16['time_to_clean_mean'])}. "
            f"Every run finished.",
            BODY,
        ),
        Paragraph(
            f"<b>Random walk.</b> It never finished within 1000 ticks. One agent cleaned "
            f"{random_1['cleaned_pct_mean']:.0f}% of the dirt on average, and four agents cleaned "
            f"{random_4['cleaned_pct_mean']:.0f}%.",
            BODY,
        ),
        Paragraph(
            f"<b>Zigzag.</b> It cleaned everything, in {fmt(zigzag_1['time_to_clean_mean'])} ticks with one agent and "
            f"{fmt(zigzag_4['time_to_clean_mean'])} with four. It touches almost every free cell "
            f"({zigzag_1['visited_pct_mean']:.0f}%), but it keeps walking over cells that are already clean, "
            f"which is why it is slower.",
            BODY,
        ),
        Spacer(1, 6),
        results_table(summary, list(summary.keys())),
        Spacer(1, 10),
        Image(str(OUTPUT / "strategies.png"), width=6.8 * inch, height=2.6 * inch),
        Paragraph("Figure 1. The three strategies, with one agent (sim1) and four agents (sim2).", BODY),
        Spacer(1, 6),
        Paragraph("4. Effect of adding agents", H2),
        Paragraph(
            f"We kept local search and changed only the number of agents. Time to clean went from "
            f"{times[0]} ticks with one agent to {times[1]} with two, {times[2]} with four, {times[3]} with eight, "
            f"and {times[4]} with sixteen. Each agent made fewer moves as the group grew, from {moves[0]} moves "
            f"down to {moves[4]}. "
            f"Going from one agent to four cut the time by about {cut_1_to_4:.0f}%. Going from eight to sixteen "
            f"cut it by only {saved_8_to_16:.0f} ticks, so each extra agent helps less "
            f"as the room gets crowded. "
            f"Our claim list stops two agents from going after the same dirt, but we did not run a version without "
            f"it, so we cannot say how much it helps.",
            BODY,
        ),
        Image(str(OUTPUT / "agent_scaling.png"), width=6.8 * inch, height=2.1 * inch),
        Paragraph("Figure 2. Local search with 1 (Simulation 1), 2, 4, 8 and 16 agents.", BODY),
        Paragraph("5. Recorded simulation data", H2),
        Paragraph("The per-run numbers (30 seeds for each setup) are in output/runs.csv, and the exact settings for "
                  "each experiment are in output/config.json. The video output/simulation.mp4 shows Simulation 1 "
                  "next to a 4-agent Simulation 2 run on the same seed.",
                  BODY),
        Paragraph("6. Conclusions", H2),
        Paragraph(
            "Local search was the best strategy here. It cleaned every run and needed the fewest moves per agent. "
            "Adding agents shortens the job a lot, though each extra agent helps less than the one before. Random "
            "walk is too slow to finish in the time limit. Zigzag gets there, but it spends a lot of its moves on "
            "cells that are already clean. The main limit of this study is the 20 x 20 room and the 4-direction "
            "movement, which we chose because each agent moves one cell at a time. Larger rooms or diagonal moves "
            "could change the ranking.",
            BODY,
        ),
    ]
    return story


def main() -> None:
    summary = load_summary()
    doc = SimpleDocTemplate(str(REPORT), pagesize=letter,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    doc.build(build_story(summary))
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
