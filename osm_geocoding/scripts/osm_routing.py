#!/usr/bin/env python3
"""
OSM Road Network Distance Calculator

Calculates road network distances using OpenStreetMap data.
Provides both geodesic (straight-line) and road network (driving) distances.

Features:
- Local road network routing (no API calls)
- Multiple distance metrics (geodesic, road distance, travel time)
- Speed limit-based travel time estimates
- Caching for performance

Usage:
    from osm_routing import OSMRouter
    router = OSMRouter()
    router.load_road_network(['arkansas'])
    distance = router.calculate_distance(origin_coords, dest_coords)
"""

import os
import time
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict

import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString
from geopy.distance import geodesic
import osmium


@dataclass
class DistanceResult:
    """Result of distance calculation."""
    geodesic_distance_miles: float
    road_distance_miles: Optional[float] = None
    travel_time_minutes: Optional[float] = None
    route_found: bool = False
    calculation_method: str = "geodesic"
    intermediate_points: List[Tuple[float, float]] = None


class OSMRoadNetworkExtractor(osmium.SimpleHandler):
    """Extract road network from OSM data for routing."""
    
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.roads = []
        self.nodes = {}
        
        # Highway types to include for routing
        self.highway_types = {
            'motorway', 'trunk', 'primary', 'secondary', 'tertiary',
            'unclassified', 'residential', 'service', 'motorway_link',
            'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'
        }
        
        # Speed limits by highway type (mph)
        self.default_speeds = {
            'motorway': 70,
            'trunk': 55,
            'primary': 45,
            'secondary': 35,
            'tertiary': 30,
            'unclassified': 25,
            'residential': 25,
            'service': 15,
            'motorway_link': 45,
            'trunk_link': 35,
            'primary_link': 30,
            'secondary_link': 25,
            'tertiary_link': 20
        }
    
    def node(self, n):
        """Store node coordinates for road network."""
        if n.location.valid():
            self.nodes[n.id] = (n.location.lon, n.location.lat)
    
    def way(self, w):
        """Process road ways for routing network."""
        if not w.tags.get('highway'):
            return
        
        highway_type = w.tags['highway']
        if highway_type not in self.highway_types:
            return
        
        # Extract way properties
        way_data = {
            'osm_id': w.id,
            'highway': highway_type,
            'name': w.tags.get('name', ''),
            'maxspeed': self._parse_speed(w.tags.get('maxspeed')),
            'oneway': w.tags.get('oneway', 'no'),
            'lanes': self._parse_lanes(w.tags.get('lanes')),
            'surface': w.tags.get('surface', 'unknown'),
            'nodes': [n.ref for n in w.nodes]
        }
        
        # Use default speed if not specified
        if way_data['maxspeed'] is None:
            way_data['maxspeed'] = self.default_speeds.get(highway_type, 25)
        
        self.roads.append(way_data)
    
    def _parse_speed(self, speed_str: Optional[str]) -> Optional[int]:
        """Parse speed limit from OSM tags."""
        if not speed_str:
            return None
        
        # Handle common formats
        if speed_str.isdigit():
            return int(speed_str)
        
        if speed_str.endswith(' mph'):
            return int(speed_str.replace(' mph', ''))
        
        if speed_str.endswith(' km/h'):
            kmh = int(speed_str.replace(' km/h', ''))
            return int(kmh * 0.621371)  # Convert to mph
        
        return None
    
    def _parse_lanes(self, lanes_str: Optional[str]) -> int:
        """Parse number of lanes."""
        if not lanes_str or not lanes_str.isdigit():
            return 1
        return int(lanes_str)


class OSMRouter:
    """Road network router using OSM data."""
    
    def __init__(self, data_dir: Optional[Path] = None, cache_dir: Optional[Path] = None):
        """Initialize router with data and cache directories."""
        if data_dir is None:
            script_dir = Path(__file__).parent
            data_dir = script_dir.parent / 'data' / 'osm_extracts'
        
        if cache_dir is None:
            script_dir = Path(__file__).parent
            cache_dir = script_dir.parent / 'data' / 'processed'
            cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        
        # Network data
        self.road_graph = None
        self.loaded_states = []
        
        # Distance calculation cache
        self.distance_cache = {}
        self.cache_file = self.cache_dir / 'distance_cache.pkl'
        self._load_cache()
    
    def load_road_network(self, states: List[str], use_cache: bool = True) -> bool:
        """Load road network from OSM data."""
        cache_key = '_'.join(sorted(states))
        graph_cache_file = self.cache_dir / f'road_graph_{cache_key}.pkl'
        
        # Try to load from cache first
        if use_cache and graph_cache_file.exists():
            print(f"📂 Loading cached road network for {', '.join(states)}...")
            try:
                with open(graph_cache_file, 'rb') as f:
                    self.road_graph = pickle.load(f)
                self.loaded_states = states
                print(f"✅ Loaded cached network: {self.road_graph.number_of_nodes()} nodes, {self.road_graph.number_of_edges()} edges")
                return True
            except Exception as e:
                print(f"⚠️ Cache loading failed: {e}")
        
        print(f"🔨 Building road network for states: {', '.join(states)}")
        
        # Extract road network from OSM files
        all_roads = []
        all_nodes = {}
        
        for state in states:
            pbf_file = self.data_dir / f"{state}-latest.osm.pbf"
            
            if not pbf_file.exists():
                print(f"⚠️ OSM data file not found: {pbf_file}")
                continue
            
            print(f"📂 Extracting road network from {state}...")
            start_time = time.time()
            
            extractor = OSMRoadNetworkExtractor()
            extractor.apply_file(str(pbf_file))
            
            print(f"  Found {len(extractor.roads)} roads")
            print(f"  Found {len(extractor.nodes)} nodes")
            
            all_roads.extend(extractor.roads)
            all_nodes.update(extractor.nodes)
            
            elapsed = time.time() - start_time
            print(f"  Processed in {elapsed:.1f} seconds")
        
        if not all_roads:
            print("❌ No road network data found")
            return False
        
        # Build NetworkX graph
        print("🔗 Building routing graph...")
        self.road_graph = self._build_routing_graph(all_roads, all_nodes)
        
        if self.road_graph is None:
            return False
        
        # Cache the graph for future use
        if use_cache:
            print("💾 Caching road network...")
            try:
                with open(graph_cache_file, 'wb') as f:
                    pickle.dump(self.road_graph, f)
            except Exception as e:
                print(f"⚠️ Cache saving failed: {e}")
        
        self.loaded_states = states
        print(f"✅ Road network ready: {self.road_graph.number_of_nodes()} nodes, {self.road_graph.number_of_edges()} edges")
        return True
    
    def _build_routing_graph(self, roads: List[Dict], nodes: Dict) -> Optional[nx.MultiDiGraph]:
        """Build NetworkX graph from road data."""
        G = nx.MultiDiGraph()
        
        # Add nodes with coordinates
        for node_id, (lon, lat) in nodes.items():
            G.add_node(node_id, x=lon, y=lat)
        
        # Add edges from roads
        edges_added = 0
        for road in roads:
            road_nodes = road['nodes']
            if len(road_nodes) < 2:
                continue
            
            # Calculate edge attributes
            for i in range(len(road_nodes) - 1):
                node1, node2 = road_nodes[i], road_nodes[i + 1]
                
                # Skip if nodes don't exist
                if node1 not in nodes or node2 not in nodes:
                    continue
                
                # Calculate distance
                coord1 = nodes[node1]
                coord2 = nodes[node2]
                distance_miles = geodesic(coord1[::-1], coord2[::-1]).miles
                
                # Calculate travel time
                speed_mph = road['maxspeed']
                travel_time_hours = distance_miles / speed_mph
                travel_time_minutes = travel_time_hours * 60
                
                # Add edge attributes
                edge_attrs = {
                    'distance_miles': distance_miles,
                    'travel_time_minutes': travel_time_minutes,
                    'speed_mph': speed_mph,
                    'highway': road['highway'],
                    'name': road['name'],
                    'osm_id': road['osm_id']
                }
                
                # Add edge (forward direction)
                G.add_edge(node1, node2, **edge_attrs)
                edges_added += 1
                
                # Add reverse edge if not oneway
                if road['oneway'] not in ['yes', 'true', '1']:
                    G.add_edge(node2, node1, **edge_attrs)
                    edges_added += 1
        
        print(f"  Added {edges_added} edges to graph")
        
        if G.number_of_nodes() == 0:
            print("❌ No valid nodes in graph")
            return None
        
        return G
    
    def calculate_distance(self, origin: Tuple[float, float], 
                         destination: Tuple[float, float],
                         include_route: bool = False) -> DistanceResult:
        """Calculate distance between two points."""
        # Always calculate geodesic distance
        geodesic_miles = geodesic(origin, destination).miles
        
        # Check cache first
        cache_key = (round(origin[0], 6), round(origin[1], 6), 
                    round(destination[0], 6), round(destination[1], 6))
        
        if cache_key in self.distance_cache:
            cached = self.distance_cache[cache_key]
            return DistanceResult(
                geodesic_distance_miles=geodesic_miles,
                road_distance_miles=cached.get('road_distance'),
                travel_time_minutes=cached.get('travel_time'),
                route_found=cached.get('route_found', False),
                calculation_method=cached.get('method', 'geodesic'),
                intermediate_points=cached.get('route_points')
            )
        
        # Try road network routing if available
        if self.road_graph is not None:
            try:
                route_result = self._calculate_road_route(origin, destination, include_route)
                
                # Cache the result
                self.distance_cache[cache_key] = {
                    'road_distance': route_result.road_distance_miles,
                    'travel_time': route_result.travel_time_minutes,
                    'route_found': route_result.route_found,
                    'method': route_result.calculation_method,
                    'route_points': route_result.intermediate_points
                }
                
                # Update geodesic distance
                route_result.geodesic_distance_miles = geodesic_miles
                return route_result
                
            except Exception as e:
                print(f"⚠️ Road routing failed: {e}")
        
        # Fall back to geodesic distance only
        return DistanceResult(
            geodesic_distance_miles=geodesic_miles,
            calculation_method="geodesic"
        )
    
    def _calculate_road_route(self, origin: Tuple[float, float], 
                            destination: Tuple[float, float],
                            include_route: bool = False) -> DistanceResult:
        """Calculate road network route between two points."""
        # Find nearest nodes to origin and destination
        origin_node = self._find_nearest_node(origin)
        dest_node = self._find_nearest_node(destination)
        
        if origin_node is None or dest_node is None:
            return DistanceResult(
                geodesic_distance_miles=0,
                calculation_method="geodesic"
            )
        
        # Calculate shortest path
        try:
            path = nx.shortest_path(self.road_graph, origin_node, dest_node, 
                                  weight='distance_miles')
            
            # Calculate total distance and time
            total_distance = 0
            total_time = 0
            route_points = []
            
            for i in range(len(path) - 1):
                edge_data = self.road_graph[path[i]][path[i + 1]]
                
                # Handle multiple edges between nodes
                if isinstance(edge_data, dict) and 'distance_miles' in edge_data:
                    edge_info = edge_data
                else:
                    # Take first edge if multiple exist
                    edge_info = list(edge_data.values())[0]
                
                total_distance += edge_info['distance_miles']
                total_time += edge_info['travel_time_minutes']
                
                # Add route point if requested
                if include_route:
                    node_data = self.road_graph.nodes[path[i]]
                    route_points.append((node_data['y'], node_data['x']))
            
            # Add final point
            if include_route and path:
                final_node_data = self.road_graph.nodes[path[-1]]
                route_points.append((final_node_data['y'], final_node_data['x']))
            
            return DistanceResult(
                geodesic_distance_miles=0,  # Will be set by caller
                road_distance_miles=total_distance,
                travel_time_minutes=total_time,
                route_found=True,
                calculation_method="road_network",
                intermediate_points=route_points if include_route else None
            )
            
        except nx.NetworkXNoPath:
            return DistanceResult(
                geodesic_distance_miles=0,
                calculation_method="geodesic"
            )
    
    def _find_nearest_node(self, point: Tuple[float, float]) -> Optional[int]:
        """Find nearest graph node to given coordinates."""
        min_distance = float('inf')
        nearest_node = None
        
        lat, lon = point
        
        # Simple brute force search (could be optimized with spatial index)
        for node_id, node_data in self.road_graph.nodes(data=True):
            node_lat, node_lon = node_data['y'], node_data['x']
            distance = geodesic((lat, lon), (node_lat, node_lon)).miles
            
            if distance < min_distance:
                min_distance = distance
                nearest_node = node_id
        
        # Only return node if within reasonable distance (1 mile)
        if min_distance < 1.0:
            return nearest_node
        
        return None
    
    def _load_cache(self):
        """Load distance calculation cache."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.distance_cache = pickle.load(f)
                print(f"📋 Loaded {len(self.distance_cache)} cached distances")
            except Exception as e:
                print(f"⚠️ Cache loading failed: {e}")
                self.distance_cache = {}
    
    def save_cache(self):
        """Save distance calculation cache."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.distance_cache, f)
            print(f"💾 Saved {len(self.distance_cache)} cached distances")
        except Exception as e:
            print(f"⚠️ Cache saving failed: {e}")
    
    def calculate_distances_batch(self, origin: Tuple[float, float], 
                                destinations: List[Tuple[float, float]]) -> List[DistanceResult]:
        """Calculate distances from one origin to multiple destinations."""
        results = []
        
        print(f"🔍 Calculating distances from origin to {len(destinations)} destinations...")
        
        for i, dest in enumerate(destinations):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(destinations)}")
            
            result = self.calculate_distance(origin, dest)
            results.append(result)
        
        # Save cache after batch processing
        self.save_cache()
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Initialize router
    router = OSMRouter()
    
    # Load Arkansas road network
    success = router.load_road_network(['arkansas'])
    
    if success:
        # Test distance calculation
        origin = (34.7465, -92.2896)  # Little Rock, AR
        destination = (36.0822, -94.1719)  # Fayetteville, AR
        
        print(f"\nTesting distance calculation:")
        print(f"Origin: {origin}")
        print(f"Destination: {destination}")
        
        result = router.calculate_distance(origin, destination, include_route=True)
        
        print(f"\nResults:")
        print(f"  Geodesic distance: {result.geodesic_distance_miles:.2f} miles")
        if result.road_distance_miles:
            print(f"  Road distance: {result.road_distance_miles:.2f} miles")
            print(f"  Travel time: {result.travel_time_minutes:.1f} minutes")
            print(f"  Route found: {result.route_found}")
        print(f"  Method: {result.calculation_method}")
        
        # Save cache
        router.save_cache()
    else:
        print("Failed to load road network")
        print("Run: python setup/download_osm_data.py --state arkansas")