from collections import defaultdict
from pathlib import Path

import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from loguru import logger

from pyvis.network import Network


class GraphService:
    """
    Service for graph operations.


    Args:
        G: Directed graph.
        dataframe: DataFrame with the data of the plates.
    """

    def __init__(self):
        self.G: nx.DiGraph | None = None
        self.dataframe: pd.DataFrame | None = None
        logger.info("Initialized Graph service.")

    def __limit_nodes_in_graph(self, G: nx.DiGraph, max_nodes: int = 30) -> nx.DiGraph:
        """
        Limits the number of nodes in the graph to improve visualization and avoid overlapping.

        Args:
            G (nx.DiGraph): The directed graph to be limited.
            max_nodes (int, default=30): Approximate reference value for the maximum number of nodes, not an exact limit.
            The algorithm prioritizes keeping nodes with higher weight (relevance) and may include a
            different number of nodes depending on the weight distribution in the graph.

        Returns:
            nx.DiGraph: The graph with a limited number of nodes.
        """
        # Count of target and batedor nodes by weight group
        weight_counts = {}
        for node, data in G.nodes(data=True):
            node_type = data.get("type")

            # For batedor nodes, get the weight of the edges
            if node_type == "batedor":
                edges = G.edges(node, data=True)
                for _, _, edge_data in edges:
                    weight = edge_data.get("weight", 0)
                    if weight not in weight_counts:
                        weight_counts[weight] = {"target": 0, "batedor": 0}
                    weight_counts[weight]["batedor"] += 1
            # For target nodes, add to counter with weight 0 (or other specific value)
            elif node_type == "target":
                if 0 not in weight_counts:
                    weight_counts[0] = {"target": 0, "batedor": 0}
                weight_counts[0]["target"] += 1

        # Sort weights in descending order
        sorted_weights = sorted(weight_counts.keys(), reverse=True)

        # Determine the minimum weight to reach at least 60 nodes
        min_weight = 1  # default value
        total_nodes = 0

        for weight in sorted_weights:
            total_nodes += (
                weight_counts[weight]["target"] + weight_counts[weight]["batedor"]
            )
            if total_nodes >= max_nodes:
                min_weight = weight
                break

        # Filter the graph to include only nodes with weight >= min_weight
        nodes_to_remove = []
        for node, data in G.nodes(data=True):
            if data.get("type") == "batedor":
                # Check if all edges of the batedor have weight < min_weight
                all_edges_below_threshold = True
                for _, _, edge_data in G.edges(node, data=True):
                    if edge_data.get("weight", 0) >= min_weight:
                        all_edges_below_threshold = False
                        break

                if all_edges_below_threshold:
                    nodes_to_remove.append(node)

        G.remove_nodes_from(nodes_to_remove)

        isolated_nodes = list(nx.isolates(G))
        G.remove_nodes_from(isolated_nodes)

        return G

    def create_graph(self, dataframe: pd.DataFrame, limit_nodes: int = 30) -> None:
        """
        Creates and displays an interactive graph from a DataFrame,
        with colored nodes, detailed tooltips, and visualization options.

        Args:
            dataframe: pandas DataFrame with the data of the plates.  Must contain, at least,
                the columns 'placa_target', 'placa', 'count_different_targets' and 'target'.
                Ideally, it should also contain columns like 'datahora_local', 'bairro', etc.
                for more detailed information in the tooltips.
            limit_nodes: Approximate threshold for the maximum number of nodes in the graph.
                        The algorithm will select the nodes with the highest weight until it reaches
                        or approaches this number, prioritizing more relevant connections.
                        It is not an exact limit, but a reference value to control the density of the graph.
        """
        logger.info(f"Creating graph from dataframe.")
        self.dataframe = dataframe

        G = nx.DiGraph()

        logger.info("Preprocessing to identify target and batedor plates.")
        # Preprocessing to identify target and batedor plates
        target_plates = set(dataframe[dataframe["target"] == True]["placa"])

        logger.info("Iterating over dataframe rows to add nodes and edges.")
        for _, row in dataframe.iterrows():
            node_type = "batedor"  # Assume batedor by default
            if row["placa"] in target_plates:
                node_type = "target"  # Overwrites if the plate is in the target list

            G.add_node(row["placa"], type=node_type, **row.to_dict())

            if not row["target"]:  # Adds edges only for batedors
                G.add_edge(row["placa"], row["placa_target"], weight=row["weight"])

        logger.info("Removing isolated nodes.")
        isolated_nodes = list(nx.isolates(G))
        G.remove_nodes_from(isolated_nodes)

        logger.info("Limiting nodes in graph.")
        G = self.__limit_nodes_in_graph(G, max_nodes=limit_nodes)

        # net.show_buttons(filter_=['physics'])  # Optional: show physics controls
        self.G = G
        logger.info("Graph created.")
        # return G

    def to_html(self):
        """
        Cria e exibe um grafo interativo a partir de um DataFrame,
        com nós coloridos, tooltips detalhados e opções de visualização.

        Args:
            df: DataFrame pandas com os dados das placas.  Deve conter, no mínimo,
                as colunas 'placa_target', 'placa', 'count_different_targets' e 'target'.
                Idealmente, deve conter também colunas como 'datahora_local', 'bairro', etc.
                para informações mais detalhadas nos tooltips.
            filename: Nome do arquivo HTML onde o grafo será salvo.
        """

        net = Network(
            height="800px",
            width="100%",
            notebook=True,
            directed=True,
            cdn_resources="remote",
        )

        for node, data in self.G.nodes(data=True):
            # Cor do nó
            if data.get("type") == "target":
                color = "red"
                size = 20
            else:
                color = "blue"
                size = 20

            net.add_node(node, label=node, color=color, size=size)

        for source, target, data in self.G.edges(data=True):
            weight = data.get("weight", 1)  # Peso padrão 1 se não houver
            net.add_edge(
                source, target, value=weight, color="black", title=f"Peso: {weight}"
            )

        net.set_options(
            """
            {
                "configure": {
                "enabled": true,
                "filter": ["physics"]
                },
                "physics": {
                "forceAtlas2Based": {
                    "theta": 0.5,
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08,
                    "damping": 0.4,
                    "avoidOverlap": 1
                },
                "maxVelocity": 50,
                "minVelocity": 0.75,
                "solver": "forceAtlas2Based",
                "timestep": 0.5
                },
                "wind":{
                "x":0,
                "y":0
                },
                "edges": {
                "smooth": {
                    "type": "dynamic"
                }
                },
                "interaction": {
                "hover": true  
                }
            }
            """
        )

        return net

    def to_png_improved(
        self, file_dir: Path | str = "./", file_name: str = "grafo.png"
    ) -> Path:
        """
        Versão aprimorada da visualização do grafo para investigação policial.

        Gera um grafo com melhor distribuição espacial e legibilidade, evitando
        sobreposição de nós e etiquetas, facilitando a identificação rápida das
        placas mais relevantes.

        Args:
            file_dir: Diretório para salvar o arquivo PNG. Padrão: "./".
            file_name: Nome do arquivo PNG. Padrão: "grafo.png".

        Returns:
            Path: Caminho para o arquivo PNG salvo.
        """
        logger.info(
            f"Convertendo grafo para PNG com layout otimizado: {file_name} em {file_dir}"
        )

        # --- Validação de entrada e manipulação de caminhos ---
        if isinstance(file_dir, str):
            file_dir = Path(file_dir)
        elif not isinstance(file_dir, Path):
            raise TypeError(
                f"file_dir deve ser uma string ou pathlib.Path, não {type(file_dir)}"
            )

        if not isinstance(file_name, str):
            raise TypeError(f"file_name deve ser uma string, não {type(file_name)}")

        file_path = file_dir / file_name

        try:
            file_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Diretório {file_dir} verificado/criado.")
        except Exception as e:
            logger.error(f"Não foi possível criar o diretório {file_dir}: {e}")
            raise IOError(f"Não foi possível criar o diretório {file_dir}") from e

        # --- Configuração da figura ---
        plt.figure(figsize=(20, 16))  # Figura maior para melhor espaçamento
        logger.debug(f"Figura matplotlib criada com tamanho (20, 16).")

        # --- Cálculo de layout aprimorado ---
        logger.info("Aplicando layout de força direcionada otimizado ao grafo.")
        try:
            # Parâmetros otimizados para maior espaçamento entre nós
            pos = nx.spring_layout(
                self.G,
                k=1.8,  # Aumentado significativamente para maior separação entre nós
                iterations=500,  # Mais iterações para melhor convergência
                seed=42,  # Para reprodutibilidade
                weight="weight",  # Usar pesos das arestas para influenciar o layout
            )

            # Ajuste adicional para evitar sobreposição de nós
            pos = adjust_positions(
                self.G, pos, min_dist=0.2
            )  # Aumentada a distância mínima

            logger.info("Layout de força direcionada otimizado calculado.")
        except Exception as e:
            logger.error(f"Erro durante cálculo de layout: {e}")
            plt.close()
            raise

        # --- Configurações visuais dinâmicas ---
        logger.info("Determinando estilos dos nós (cor, tamanho, forma, borda).")

        # Estilos visuais aprimorados
        styles = {
            "target": {
                "color": "red",
                "size": 800,  # Tamanho aumentado
                "shape": "o",  # Círculo
                "border_color": "darkred",
                "border_width": 2.5,
                "label_offset": 0.04,  # Offset da etiqueta
                "zorder": 30,  # Ordem de desenho (maior = em cima)
            },
            "batedor": {
                "color": "royalblue",  # Azul mais vibrante
                "size": 500,
                "shape": "o",  # Quadrado
                "border_color": "navy",
                "border_width": 2.0,
                "label_offset": 0.04,
                "zorder": 20,
            },
            "other": {
                "color": "lightgray",
                "size": 300,
                "shape": "d",  # Diamante
                "border_color": "gray",
                "border_width": 1.0,
                "label_offset": 0.035,
                "zorder": 10,
            },
        }

        # Coletar estilos para cada nó
        node_props = {}
        for node in self.G.nodes():
            node_type = self.G.nodes[node].get("type", "other")
            node_props[node] = styles.get(node_type, styles["other"])

        logger.debug("Estilos dos nós determinados.")

        # --- Normalização da largura das arestas ---
        logger.info("Normalizando larguras das arestas com base no peso.")
        edge_props = {}

        # Obter pesos das arestas
        edge_weights = [d.get("weight", 1) for _, _, d in self.G.edges(data=True)]

        if edge_weights:
            min_w, max_w = min(edge_weights), max(edge_weights)
            base_width = 0.8  # Largura mínima das arestas
            max_width = 8.0  # Largura máxima das arestas

            if max_w == min_w:
                # Se todos os pesos forem iguais
                for u, v, d in self.G.edges(data=True):
                    rad_value = 0.15  # Curvatura padrão
                    # Adicionar variação na curvatura para evitar sobreposição
                    if self.G.has_edge(v, u):  # Se existir aresta na direção oposta
                        rad_value = 0.25  # Maior curvatura

                    edge_props[(u, v)] = {
                        "width": base_width,
                        "alpha": 0.7,
                        "weight": 1,  # Peso padrão para ordenação
                        "rad": rad_value,
                    }
            else:
                # Escalonar as larguras com base nos pesos
                range_w = max_w - min_w
                range_output = max_width - base_width

                for u, v, d in self.G.edges(data=True):
                    weight = d.get("weight", 1)
                    width = base_width + range_output * (weight - min_w) / range_w
                    # Arestas mais pesadas ficam mais escuras
                    alpha = min(0.9, 0.5 + 0.4 * (weight - min_w) / range_w)

                    # Usar curvatura variável para evitar sobreposição
                    rad_value = 0.15  # Valor base para curvatura

                    # Se existir aresta na direção oposta, aumentar curvatura
                    if self.G.has_edge(v, u):
                        rad_value = 0.25

                    # Se o peso for muito alto, reduzir um pouco a curvatura para arestas importantes
                    if weight > (max_w - min_w) * 0.7 + min_w:
                        rad_value *= 0.8

                    edge_props[(u, v)] = {
                        "width": width,
                        "alpha": alpha,
                        "weight": weight,  # Mantenha o peso original para ordenação
                        "rad": rad_value,
                    }

            logger.debug(
                f"Pesos das arestas escalonados de [{min_w}, {max_w}] para [{base_width}, {max_width}]."
            )
        else:
            logger.debug("Nenhuma aresta encontrada.")

        # --- Desenho do grafo em camadas ---
        # 1. Desenhar arestas primeiro
        logger.info("Desenhando arestas.")
        # Desenhar arestas em ordem de peso (do menor para o maior)
        # para que as arestas mais importantes fiquem por cima
        sorted_edges = sorted(edge_props.items(), key=lambda x: x[1]["weight"])

        for (u, v), props in sorted_edges:
            # NetworkX não suporta zorder diretamente, então usamos a ordem de desenho
            # para controlar quais arestas ficam por cima
            nx.draw_networkx_edges(
                self.G,
                pos,
                edgelist=[(u, v)],
                width=props["width"],
                alpha=props["alpha"],
                edge_color="black",
                arrows=True,
                arrowstyle="-|>",
                arrowsize=15,
                connectionstyle=f"arc3,rad={props['rad']}",  # Curvatura personalizada por aresta
            )

        # 2. Desenhar nós agrupados por tipo
        logger.info("Desenhando nós por tipo.")
        # Agrupar nós por tipo para desenhar em camadas
        node_by_type = {"target": [], "batedor": [], "other": []}

        for node in self.G.nodes():
            node_type = self.G.nodes[node].get("type", "other")
            # Garantir que o tipo é conhecido
            if node_type not in node_by_type:
                node_type = "other"
            node_by_type[node_type].append(node)

        # Desenhar cada tipo de nó separadamente, começando pelos menos importantes
        for node_type in [
            "batedor",
            "target",
        ]:  # Ordem de desenho (outros, batedores, alvos)
            if not node_by_type[node_type]:
                continue

            style = styles[node_type]
            nx.draw_networkx_nodes(
                self.G,
                pos,
                nodelist=node_by_type[node_type],
                node_color=style["color"],
                node_size=style["size"],
                node_shape=style["shape"],
                alpha=0.9,
                linewidths=style["border_width"],
                edgecolors=style["border_color"],
                # zorder=style["zorder"],
            )

        logger.debug("Nós desenhados em camadas.")

        # 3. Desenhar etiquetas com posições otimizadas
        logger.info("Desenhando etiquetas dos nós com posicionamento otimizado.")

        # Criar etiquetas com formatação melhorada
        for node, (x, y) in pos.items():
            node_type = self.G.nodes[node].get("type", "other")
            style = styles.get(node_type, styles["other"])

            # Calcular offset da etiqueta com base no tipo do nó
            label_offset = style["label_offset"]

            # Criar caixa de fundo com cantos arredondados e borda
            bbox_props = {
                "boxstyle": "round,pad=0.4",
                "fc": "white",
                "ec": style["border_color"],
                "alpha": 0.9,
                "lw": 1,
            }

            # Tamanho da fonte com base na importância do nó
            if node_type == "target":
                fontsize = 11
                fontweight = "bold"
            elif node_type == "batedor":
                fontsize = 10
                fontweight = "normal"
            else:
                fontsize = 9
                fontweight = "normal"

            plt.text(
                x,
                y + label_offset,
                str(node),
                fontsize=fontsize,
                fontweight=fontweight,
                ha="center",
                va="center",
                bbox=bbox_props,
                zorder=style["zorder"] + 5,  # Sempre acima do nó correspondente
            )

        logger.debug("Etiquetas desenhadas com posicionamento otimizado.")

        # --- Ajustes finais e salvamento ---
        plt.axis("off")
        plt.tight_layout(pad=0.4)

        # Adicionar título informativo

        logger.info(f"Salvando imagem do grafo em {file_path}")
        try:
            plt.savefig(file_path, dpi=300, bbox_inches="tight", pad_inches=0.2)
            logger.info(f"Imagem do grafo salva com sucesso em {file_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar imagem do grafo em {file_path}: {e}")
            plt.close()
            raise

        plt.close()
        logger.debug("Figura matplotlib fechada.")

        return file_path


def adjust_positions(G, pos, min_dist=0.1):
    """
    Ajusta as posições dos nós para evitar sobreposição.

    Args:
        G: Grafo NetworkX
        pos: Dicionário de posições dos nós
        min_dist: Distância mínima desejada entre nós

    Returns:
        Dicionário atualizado de posições
    """
    pos_new = pos.copy()
    nodes = list(G.nodes())

    # Ajuste iterativo para evitar sobreposição
    max_iterations = 50
    for _ in range(max_iterations):
        moved = False
        for i, node1 in enumerate(nodes):
            for node2 in nodes[i + 1 :]:
                # Calcular distância entre nós
                x1, y1 = pos_new[node1]
                x2, y2 = pos_new[node2]
                dx = x2 - x1
                dy = y2 - y1
                dist = (dx**2 + dy**2) ** 0.5

                # Se nós estão muito próximos, ajustar posições
                if dist < min_dist:
                    # Vetor unitário na direção oposta
                    if dist > 0:
                        dx /= dist
                        dy /= dist
                    else:
                        # Se dist=0 (nós sobrepostos), mova em direção aleatória
                        import random
                        import math

                        angle = random.uniform(0, 2 * 3.14159)
                        dx = math.cos(angle)
                        dy = math.sin(angle)

                    # Calcular deslocamento necessário
                    move = (min_dist - dist) / 2

                    # Ajustar ambos os nós em direções opostas
                    pos_new[node1] = (x1 - dx * move, y1 - dy * move)
                    pos_new[node2] = (x2 + dx * move, y2 + dy * move)
                    moved = True

        # Se nenhum nó foi movido, saímos do loop
        if not moved:
            break

    return pos_new
