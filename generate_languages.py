#!/usr/bin/env python3

import json
import os
import urllib.request
from pathlib import Path


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ.get("GITHUB_TOKEN")

OUTPUT = Path("assets/languages.svg")

MAX_LANGUAGES = 8

# Linguagens que normalmente não representam código-fonte relevante
# para este tipo de estatística.
IGNORED_LANGUAGES = {
    "Jupyter Notebook",
}


def github_request(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": USERNAME,
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def get_repositories():
    repositories = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?type=owner&per_page=100&page={page}"
        )

        batch = github_request(url)

        if not batch:
            break

        repositories.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    return repositories


def collect_languages(repositories):
    languages = {}

    for repository in repositories:
        name = repository["name"]

        # O próprio README não entra na estatística.
        if name == USERNAME:
            continue

        # Forks não representam diretamente projetos do usuário.
        if repository["fork"]:
            continue

        print(f"Reading {name}...")

        url = (
            f"https://api.github.com/repos/"
            f"{USERNAME}/{name}/languages"
        )

        repository_languages = github_request(url)

        for language, bytes_count in repository_languages.items():
            if language in IGNORED_LANGUAGES:
                continue

            languages[language] = (
                languages.get(language, 0) + bytes_count
            )

    return languages


def normalize_languages(languages):
    ordered = sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if len(ordered) <= MAX_LANGUAGES:
        return ordered

    top = ordered[:MAX_LANGUAGES]
    other = sum(value for _, value in ordered[MAX_LANGUAGES:])

    return top + [("Other", other)]


def escape_svg(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_svg(languages):
    total = sum(value for _, value in languages)

    if total == 0:
        raise RuntimeError("No language data found.")

    width = 760
    height = 170

    bar_x = 20
    bar_y = 42
    bar_width = 720
    bar_height = 12

    # GitHub-like language colors.
    colors = {
        "TypeScript": "#3178c6",
        "JavaScript": "#f1e05a",
        "Java": "#b07219",
        "Python": "#3572A5",
        "CSS": "#563d7c",
        "HTML": "#e34c26",
        "Shell": "#89e051",
        "C": "#555555",
        "C++": "#f34b7d",
        "C#": "#178600",
        "Go": "#00ADD8",
        "Rust": "#dea584",
        "PHP": "#4F5D95",
        "Kotlin": "#A97BFF",
        "Dart": "#00B4AB",
        "Ruby": "#701516",
        "Swift": "#F05138",
        "Vue": "#41b883",
        "Other": "#8b949e",
    }

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: -apple-system, BlinkMacSystemFont, "
        "'Segoe UI', sans-serif; }",
        ".title { font-size: 16px; font-weight: 600; }",
        ".label { font-size: 12px; }",
        ".percent { font-size: 12px; opacity: .65; }",
        "</style>",
        '<rect width="100%" height="100%" fill="transparent"/>',
        '<text x="20" y="24" class="title">Languages</text>',
    ]

    # Language bar
    current_x = bar_x

    for language, value in languages:
        percentage = value / total
        segment_width = bar_width * percentage

        color = colors.get(language, "#8b949e")

        svg.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" '
            f'width="{segment_width:.2f}" height="{bar_height}" '
            f'fill="{color}"/>'
        )

        current_x += segment_width

    # Legend
    columns = 4
    column_width = 180
    row_height = 32
    start_y = 82

    for index, (language, value) in enumerate(languages):
        percentage = value / total * 100

        column = index % columns
        row = index // columns

        x = 20 + column * column_width
        y = start_y + row * row_height

        color = colors.get(language, "#8b949e")

        svg.append(
            f'<circle cx="{x}" cy="{y - 4}" r="5" fill="{color}"/>'
        )

        svg.append(
            f'<text x="{x + 12}" y="{y}" class="label">'
            f'{escape_svg(language)}</text>'
        )

        svg.append(
            f'<text x="{x + 12}" y="{y + 15}" class="percent">'
            f'{percentage:.1f}%</text>'
        )

    svg.append("</svg>")

    return "\n".join(svg)


def main():
    repositories = get_repositories()

    print(f"Found {len(repositories)} repositories.")

    languages = collect_languages(repositories)
    languages = normalize_languages(languages)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        generate_svg(languages),
        encoding="utf-8",
    )

    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
