#!/usr/bin/env python3

import json
import os
import urllib.request
from pathlib import Path


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ.get("GITHUB_TOKEN")

OUTPUT_DIR = Path("assets")

# Cor do texto para cada tema do GitHub.
THEMES = {
    "light": "#1f2328",
    "dark": "#e6edf3",
}

# Categoria de cada linguagem, por finalidade. Linguagens que não
# aparecem aqui entram em "Other".
CATEGORIES = {
    "Web": {
        "TypeScript", "JavaScript", "HTML", "CSS", "SCSS", "Sass", "Less",
        "Vue", "Svelte", "Astro", "EJS", "Handlebars", "Pug", "Jinja",
        "Blade", "Twig", "PHP", "Ruby", "Elm",
    },
    "Automation": {
        "Python", "Shell", "PowerShell", "Batchfile", "Perl", "Lua",
        "Dockerfile", "Makefile", "CMake", "Nix", "HCL", "Procfile",
        "Vim Script", "Emacs Lisp",
    },
    "Docs": {
        "TeX", "Typst", "Markdown", "MDX",
    },
    "Data & Math": {
        "R", "Julia", "MATLAB", "Fortran", "SQL", "PLpgSQL", "TSQL",
    },
    "Systems": {
        "C", "C++", "Rust", "Go", "Zig", "Nim", "Assembly", "Cuda",
        "GLSL", "Objective-C",
    },
    "Apps": {
        "Java", "Kotlin", "Swift", "Dart", "C#", "Scala", "Groovy",
        "Elixir", "Erlang", "Clojure",
    },
}

# Cores escolhidas para ter contraste nos temas claro e escuro.
CATEGORY_COLORS = {
    "Web": "#3178c6",
    "Automation": "#f0883e",
    "Docs": "#2ea043",
    "Data & Math": "#a371f7",
    "Systems": "#db61a2",
    "Apps": "#39c5cf",
    "Other": "#8b949e",
}


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


def group_by_category(languages):
    categories = {}

    for language, bytes_count in languages.items():
        category = next(
            (
                name
                for name, members in CATEGORIES.items()
                if language in members
            ),
            "Other",
        )

        categories[category] = (
            categories.get(category, 0) + bytes_count
        )

    # Maiores primeiro, "Other" sempre por último.
    return sorted(
        categories.items(),
        key=lambda item: (item[0] == "Other", -item[1]),
    )


def escape_svg(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_svg(categories, text_color):
    total = sum(value for _, value in categories)

    if total == 0:
        raise RuntimeError("No language data found.")

    # Layout: legenda em grade, altura ajustada ao número de linhas.
    columns = 4
    column_width = 190
    row_height = 32
    start_y = 50
    rows = -(-len(categories) // columns)

    width = 760
    height = start_y + (rows - 1) * row_height + 23

    bar_x = 0
    bar_y = 10
    bar_width = width
    bar_height = 12

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<style>",
        "text { font-family: -apple-system, BlinkMacSystemFont, "
        f"'Segoe UI', sans-serif; fill: {text_color}; }}",
        ".label { font-size: 12px; }",
        ".percent { font-size: 12px; opacity: .65; }",
        "</style>",
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]

    # Category bar
    current_x = bar_x

    for category, value in categories:
        percentage = value / total
        segment_width = bar_width * percentage

        color = CATEGORY_COLORS[category]

        svg.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" '
            f'width="{segment_width:.2f}" height="{bar_height}" '
            f'fill="{color}"/>'
        )

        current_x += segment_width

    # Legend
    for index, (category, value) in enumerate(categories):
        percentage = value / total * 100

        column = index % columns
        row = index // columns

        # Círculo encostado na borda esquerda (cx = raio).
        x = 5 + column * column_width
        y = start_y + row * row_height

        color = CATEGORY_COLORS[category]

        svg.append(
            f'<circle cx="{x}" cy="{y - 4}" r="5" fill="{color}"/>'
        )

        svg.append(
            f'<text x="{x + 12}" y="{y}" class="label">'
            f'{escape_svg(category)}</text>'
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
    categories = group_by_category(languages)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for theme, text_color in THEMES.items():
        output = OUTPUT_DIR / f"languages-{theme}.svg"
        output.write_text(
            generate_svg(categories, text_color),
            encoding="utf-8",
        )

        print(f"Generated {output}")


if __name__ == "__main__":
    main()
