"""Genera radar charts para el benchmarking competitivo.

Solo este módulo importa matplotlib; domain/ no lo importa directamente.
"""

import math
import os

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # backend sin display (headless en WSL)


def generate_radar_chart(
    data: dict[str, list[float]],
    labels: list[str],
    output_path: str,
    title: str = "Benchmarking de Competidores",
) -> str:
    """Genera PNG con radar chart y lo guarda en output_path.

    Args:
        data: {nombre_competidor: [score_dim1, ..., score_dimN]}
        labels: etiquetas de cada dimensión (len == len(scores))
        output_path: ruta destino del PNG
        title: título del gráfico

    Returns:
        output_path tras guardar el archivo.
    """
    n = len(labels)
    angles = [i * 2 * math.pi / n for i in range(n)]
    angles += angles[:1]  # cierra el polígono

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=7, color="grey")

    colors = plt.cm.tab10.colors  # type: ignore[attr-defined]
    for idx, (competitor, scores) in enumerate(data.items()):
        values = scores + scores[:1]
        color = colors[idx % len(colors)]
        ax.plot(angles, values, linewidth=1.5, linestyle="solid", color=color, label=competitor)
        ax.fill(angles, values, alpha=0.08, color=color)

    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    ax.set_title(title, pad=20, fontsize=11, fontweight="bold")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output_path


def generate_placeholder_radar(output_path: str, empresa: str = "") -> str:
    """Genera radar chart con 5 competidores y dimensiones estándar (placeholder).

    Útil cuando no se dispone de datos estructurados del LLM.
    """
    labels = ["Innovación", "Inversión", "Presencia global", "Sostenibilidad", "Digital"]
    data = {
        "Líder global A": [4.5, 4.0, 5.0, 3.5, 4.0],
        "Líder global B": [3.5, 4.5, 4.5, 3.0, 3.5],
        "Referente LatAm": [3.0, 3.0, 2.5, 3.5, 2.5],
        "Startup FoodTech": [4.5, 2.5, 1.5, 4.0, 5.0],
        empresa or "Empresa analizada": [3.0, 3.5, 2.0, 3.5, 3.0],
    }
    title = f"Posicionamiento Competitivo{' — ' + empresa if empresa else ''}"
    return generate_radar_chart(data, labels, output_path, title)
