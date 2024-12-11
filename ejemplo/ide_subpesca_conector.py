'''
Requiere instalar requirements 
la base de datos debe tener instalado postgis
'''

import requests
import sys
import os
import json
import pandas as pd
import logging
from shapely.geometry import Polygon
from sqlalchemy import create_engine
from sqlalchemy import text
from datetime import datetime


def execute_sql_query(mapstore_engine, sql_query, ):

    with mapstore_engine.connect().execution_options(autocommit=True) as con:
        con.execute(sql_query)
        con.commit()
    print("[OK] - SQL query successfully executed")

def open_sql_query(sql_file, ):

    with open("./sql_queries/" + sql_file, encoding = "utf8") as file:
        sql_query = text(file.read())
    print("[OK] - " + sql_file + " SQL file successfully opened")
    return sql_query
 
def df_to_db(df, config_data, mapstore_engine, table_name, ):

    df.to_sql(table_name, 
                mapstore_engine, 
                if_exists = 'replace', 
                schema = config_data['base_datos']['schema'], 
                index = False)

    print("[OK] - " + table_name + " dataframe successfully copied to Mapstore database")

def create_mapstore_engine(mapstore_connection, ):

    try:
        mapstore_engine = create_engine(mapstore_connection)
        print("[OK] - SQLAlchemy engine succesfully generated")
        return mapstore_engine

    except Exception as e:
        print('[ERROR] - Creating DB engine')
        print(e)
        sys.exit(2)

def create_mapstore_connection(config_data, ):

    mapstore_connection = 'postgresql://{}:{}@{}:{}/{}'.format(
        config_data['base_datos']['user'],
        config_data['base_datos']['passwd'], 
        config_data['base_datos']['host'], 
        config_data['base_datos']['port'], 
        config_data['base_datos']['db'])
    print("[OK] - Connection string successfully generated")

    return mapstore_connection   

def drop_str_geometry(df, ):

    df.drop('geometry.rings', axis=1, inplace=True)
    print("[OK] - Old geometry column successfully dropped")
    return df

def transform_geometry_column(df, ):

    df["geometry"] = df["geometry"].apply(Polygon).apply(str)
    print("[OK] - Geometry column format successfully converted")
    return df

def polygon_coords_to_df(df, coord_list, ):

    df["geometry"] = coord_list
    print("[OK] - New geometry column successfully appended")
    return df

def list_to_tuples(df, ):

    coord_list = [[*map(tuple, row[0])] for row in df["geometry.rings"].values]
    print("[OK] - List of lists successfully converted to list of tuples")
    return coord_list

def rename_df_columns(df, ):

    df = df.rename(columns = lambda row: row.lstrip('attributes.'))
    print("[OK] - DataFrame columns successfully renamed")
    return df

def json_to_df(json_response, ):

    df = pd.json_normalize(json_response['features'])
    print("[OK] - JSON successfully transformed to DataFrame")
    return df

def get_config(filepath=""):

    if filepath == "":
        sys.exit("[ERROR] - Config filepath empty.")

    with open(filepath) as json_file:
        data = json.load(json_file)

    if data == {}:
        sys.exit("[ERROR] - Config file is empty.")

    return data

def get_parameters(argv):

    config_filepath = argv[1]
    return config_filepath

def response_to_json(ide_response, ):

    json_response = ide_response.json()
    print("[OK] - IDE rest api service succesfully transformed")
    return json_response

def get_ide_response(config_data, service, ):

    ide_response = requests.get(config_data["ide_subpesca"]["request_url"][service], headers = config_data["ide_subpesca"]["headers"])
    print("[OK] - ArcGIS rest API " + service + " service succesfully requested")
    return ide_response

def main(argv):
    start = datetime.now()
    
    #json agregado 
    argv = ["ide_subpesca_conector.py", "config.json"]

    # Get parameters
    config_filepath = get_parameters(argv)

    # Get service config parameters
    config_data = get_config(config_filepath)

    # Get responses from arcgis rest services
    centros_response = get_ide_response(config_data, "centros")

    # Tranform responses to dictionary
    centros_json = response_to_json(centros_response)

    # # Transform dictionarys to DataFrames
    centros_df = json_to_df(centros_json)
    
    # # Rename DataFrame's columns
    centros_df = rename_df_columns(centros_df)

    # # Transform the list of list of coordinates to list of tuples
    centros_df_coord_list = list_to_tuples(centros_df)

    # # Append new column to DataFrame
    centros_df = polygon_coords_to_df(centros_df, centros_df_coord_list)

    # # Change format of the geometry column
    centros_df = transform_geometry_column(centros_df)

    # # Drop the old geometry column
    centros_df = drop_str_geometry(centros_df)

    # # Create string with the db mapstore parameters
    mapstore_connection = create_mapstore_connection(config_data)

    # # Create sqlalchemy engine based on the mapstore db paramters
    mapstore_engine = create_mapstore_engine(mapstore_connection)

    # # Copy the DataFrame to the mapstore database
    df_to_db(centros_df, config_data, mapstore_engine, "concesiones_acuicultura")

    # # Open the 'add_geometry_to_services.sql' file
    geom_sql_query = open_sql_query("add_geometry_to_services.sql")

    # # Execute the SQL query to transform the geometry type of the new tables
    execute_sql_query(mapstore_engine, geom_sql_query)

    end = datetime.now()

    print(f"[OK] - Tables successfully copied to mapstore's database. Time elapsed: {end - start}")

if __name__ == "__main__":
    main(sys.argv)

