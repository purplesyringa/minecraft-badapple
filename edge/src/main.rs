use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Deserialize)]
struct Graph {
    vertices: Vec<Vertex>,
    edges: Vec<Edge>,
}

#[derive(Serialize, Deserialize, Copy, Clone)]
struct Vertex([u8; 4]);

#[derive(Deserialize, Copy, Clone)]
struct Edge {
    a: usize,
    b: usize,
    w: usize,
}

#[derive(Copy, Clone)]
struct Link {
    v: usize,
    w: usize,
}

const MAX_SUBGRAPH_SIZE: usize = 64;

struct Bruteforcer {
    graph: Graph,
    matrix: HashMap<(usize, usize), usize>,
    subgraph: Vec<usize>,
    subgraph_weight: usize,
    edges_to_right: Vec<Vec<Link>>,
    upper_limits: Vec<Vec<usize>>,
    best_weight_so_far: usize,
    best_subgraph_so_far: Vec<usize>,
}

impl Bruteforcer {
    fn new(graph: Graph) -> Self {
        let matrix = graph
            .edges
            .iter()
            .map(|edge| ((edge.a.min(edge.b), edge.a.max(edge.b)), edge.w))
            .collect();

        let mut edges_to_right = vec![Vec::new(); graph.vertices.len()];
        for edge in &graph.edges {
            edges_to_right[edge.a].push(Link {
                v: edge.b,
                w: edge.w,
            });
        }

        let mut edge_weights = Vec::new();
        let mut upper_limits = vec![Vec::new(); graph.vertices.len()];
        for u in (0..graph.vertices.len()).rev() {
            for link in &edges_to_right[u] {
                edge_weights.push(link.w);
            }
            edge_weights.sort_by_key(|&w| std::cmp::Reverse(w));

            let upper_limits = &mut upper_limits[u];
            upper_limits.push(0);
            let mut prev_index = 0;
            for subgraph_size_left in 1..=MAX_SUBGRAPH_SIZE {
                let i = edge_weights
                    .len()
                    .min(subgraph_size_left * (subgraph_size_left - 1) / 2);
                upper_limits.push(
                    upper_limits.last().unwrap()
                        + edge_weights[prev_index..i].iter().sum::<usize>(),
                );
                prev_index = i;
            }
        }

        Self {
            graph,
            matrix,
            subgraph: Vec::new(),
            subgraph_weight: 0,
            edges_to_right,
            upper_limits,
            best_weight_so_far: 0,
            best_subgraph_so_far: Vec::new(),
        }
    }

    fn run(&mut self, next_vertex: usize) {
        if self.subgraph_weight > self.best_weight_so_far {
            eprintln!(
                "At {:?}, new record: {}",
                self.subgraph, self.subgraph_weight
            );
            self.best_weight_so_far = self.subgraph_weight;
            self.best_subgraph_so_far = self.subgraph.clone();
        }

        if next_vertex == self.graph.vertices.len() || self.subgraph.len() == MAX_SUBGRAPH_SIZE {
            eprintln!("At {:?}, getting limited", self.subgraph);
            return;
        }

        // eprintln!("At {:?}, considering {}", self.subgraph, next_vertex);

        let right_subgraph_size_limit = MAX_SUBGRAPH_SIZE - self.subgraph.len();

        let right_subgraph_weight_limit = self.upper_limits[next_vertex][right_subgraph_size_limit];

        if self.subgraph_weight + right_subgraph_weight_limit <= self.best_weight_so_far {
            let cross_subgraph_weight_limit = if right_subgraph_size_limit == 0 {
                0
            } else {
                let mut cross_weight_by_right_vertex = vec![0; self.graph.vertices.len()];
                for &u in &self.subgraph {
                    for link in &self.edges_to_right[u] {
                        if link.v >= next_vertex {
                            cross_weight_by_right_vertex[link.v] += link.w;
                        }
                    }
                }

                let offset = self.graph.vertices.len() - right_subgraph_size_limit;
                cross_weight_by_right_vertex.select_nth_unstable(offset);
                cross_weight_by_right_vertex[offset..].iter().sum()
            };

            let weight_limit =
                self.subgraph_weight + cross_subgraph_weight_limit + right_subgraph_weight_limit;
            if weight_limit <= self.best_weight_so_far {
                // eprintln!(
                //     "Weight limit at {:?} is {}",
                //     self.subgraph, cross_subgraph_weight_limit
                // );
                return;
            }
        }

        // Take
        if self.subgraph.len() < MAX_SUBGRAPH_SIZE {
            let weight_diff: usize = self
                .subgraph
                .iter()
                .filter_map(|&v| self.matrix.get(&(v, next_vertex)))
                .sum();
            self.subgraph_weight += weight_diff;
            self.subgraph.push(next_vertex);
            self.run(next_vertex + 1);
            self.subgraph.pop();
            self.subgraph_weight -= weight_diff;
        }

        // Don't take
        // self.run(next_vertex + 1);
    }
}

fn main() {
    let graph: Graph = serde_json::from_slice(&std::fs::read("../graph.json").expect("load graph"))
        .expect("parse graph");

    // Reorder vertices by decreasing total degree
    let graph = {
        let mut vertices_ordered_by_weight: Vec<_> =
            (0..graph.vertices.len()).map(|i| (i, 0)).collect();
        for edge in &graph.edges {
            vertices_ordered_by_weight[edge.a].1 += edge.w;
            vertices_ordered_by_weight[edge.b].1 += edge.w;
        }
        vertices_ordered_by_weight.sort_by_key(|&(_, w)| std::cmp::Reverse(w));
        let mut old_to_new = vec![0; graph.vertices.len()];
        for (i, (j, _)) in vertices_ordered_by_weight.iter().enumerate() {
            old_to_new[*j] = i;
        }
        Graph {
            vertices: vertices_ordered_by_weight
                .into_iter()
                .map(|(i, _)| graph.vertices[i])
                .collect(),
            edges: graph
                .edges
                .into_iter()
                .map(|edge| Edge {
                    a: old_to_new[edge.a],
                    b: old_to_new[edge.b],
                    w: edge.w,
                })
                .collect(),
        }
    };

    let total_weight: usize = graph.edges.iter().map(|edge| edge.w).sum();

    let mut bruteforcer = Bruteforcer::new(graph);
    bruteforcer.run(0);

    eprintln!(
        "Best weight: {} ({:.2}%)",
        bruteforcer.best_weight_so_far,
        (bruteforcer.best_weight_so_far as f64) / (total_weight as f64) * 100.0
    );
    let subgraph = bruteforcer.best_subgraph_so_far;
    eprintln!("Subgraph: {:?}", subgraph);

    let subgraph_vertices: Vec<Vertex> = subgraph
        .iter()
        .map(|&v| bruteforcer.graph.vertices[v])
        .collect();
    println!("{}", serde_json::to_string(&subgraph_vertices).unwrap());
}
