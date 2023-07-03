#!/bin/python3
import osmnx as ox
import networkx as nx
import os
import geopandas as gp
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
import json
import time
import folium  # type: ignore
import logging


class Unique_locations:
    def __init__(self, name, coords, category, weight):
        self.name = name
        self.coords = coords
        self.category = category
        self.weight = weight


def load_private_locations():
    if os.path.exists('private_locations.json'):
        with open('private_locations.json', 'r') as file:
            json_data = json.loads(file.read())
        return json_data
    else:
        return []


def get_weed_locations(locations):
    response = requests.get(
        "https://weedmaps.com/dispensaries/in/spain/barcelona/barcelona/eixample/la-dreta-de-leixample")
    soup = BeautifulSoup(response.content, 'html.parser')
    ul_element = soup.find(
        "ul", attrs={"data-testid": "map-listings-list-wrapper"})
    li_items = ul_element.find_all("li")  # type: ignore
    for li in li_items:
        div_elements = li.find_all(
            "div", class_="legacy-base-card__Info-sc-uvyu3g-4 ybvnY")
        for div in div_elements:
            a_element = div.find("a")
            if a_element:
                link = a_element.get("href")
                parsed_url = urlparse(link)
                name = parsed_url.path.split("/")[-1]
                response = requests.get(
                    f"https://api-g.weedmaps.com/discovery/v1/listings/dispensaries/{name}")
                response_json = json.loads(response.content)
                coords = (response_json['data']['listing']['latitude'],
                          response_json['data']['listing']['longitude'])
                print(coords)
                time.sleep(0.5)
                locations.append(Unique_locations(name, coords, "weedshop", 1))


def get_graph():
    if (os.path.exists('graph.osm')):
        G = ox.load_graphml('graph.osm')
    else:
        G = ox.graph_from_point((41.405264, 2.173239),
                                dist=1500, network_type='walk')
        ox.save_graphml(G, 'graph.osm')
    return G


def export_locations_to_json(new_object, file_path):
    file_exists = os.path.isfile(file_path)
    if file_exists:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
    else:
        json_data = []
    existing_object = next(
        (obj for obj in json_data if obj['name'] == new_object.name), None)
    if existing_object is None:
        json_data.append(vars(new_object))
        with open(file_path, 'w') as file:
            json.dump(json_data, file, indent=4)
        print(f"Object '{new_object.name}' inserted and file overwritten.")
    else:
        print(f"Object '{new_object.name}' already exists in the JSON file.")


def main():
    if os.path.exists("locations.json"):
        with open("locations.json", 'r') as file:
            locations_list = json.load(file)
    else:
        locations_list = []

    home_list = load_private_locations()

    # LOAD WEED MAPS LOCATIONS
    # get_weed_locations(locations_list)
    # for location in locations_list:
    #     export_locations_to_json(location, "locations.json")

    # CREATE MAP
    G = get_graph()
    gdf = ox.graph_to_gdfs(G)
    map = gp.GeoDataFrame(gdf[0])  # type: ignore
    folium_map = map.explore()

    route_list = []
    for home in home_list:
        for location in locations_list:
            try:
                origin_node = ox.nearest_nodes(
                    G, home['coords'][1], home['coords'][0])
                destination_node, dist = ox.nearest_nodes(
                    G, location['coords'][1], location['coords'][0], return_dist=True)
                if dist > 100:
                    continue
                route = nx.shortest_path(
                    G, source=origin_node, target=destination_node, weight='length')
                route_list.append(route)
            except:
                logging.warning(f"Target not in G: {location['coords']}")
        fig, ax = ox.plot_graph_routes(
            G, route_list)
    for route in route_list:
        ox.plot_route_folium(G, route=route, route_map=folium_map,route_linewidth=6, node_size=0, bgcolor='k')
    for location in locations_list:
        marker = folium.Marker(
            location=[location['coords'][0], location['coords'][1]], popup=location['name'], icon=folium.Icon(color='green'))
        marker.add_to(folium_map)
    for home in home_list:
        marker = folium.Marker(
            location=[home['coords'][0], home['coords'][1]], popup=home['name'], icon=folium.Icon(color='blue'))
        marker.add_to(folium_map)
    folium_map.save('map.html')


if __name__ == "__main__":
    main()
