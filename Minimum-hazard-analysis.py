import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
from osgeo import ogr
import json
from networkx.readwrite import json_graph

"""
In this cell, we read shapefiles for the anlaysis and check the information
"""
### Road files and read information

## read shapefiles
pop_ds = ogr.Open('population point layer.shp')
pop_lyr = pop_ds.GetLayer()
shelter_ds = ogr.Open('shelter location point layer.shp')
shelter_lyr = shelter_ds.GetLayer()
road_ds = ogr.Open('road network line layer.shp')
road_lyr = road_ds.GetLayer()

## Get field name of road network
rfn = [] #road field name
road_field = road_lyr.GetLayerDefn()
for n in range(road_field.GetFieldCount()) :
        name = road_field.GetFieldDefn(n).name
        rfn.append(name)
rfn.append('Y')
rfn.append('X')

## Get field name and type of pop layer
pfn = [] #road field name
pop_field = pop_lyr.GetLayerDefn()
for n in range(pop_field.GetFieldCount()) :
        name = pop_field.GetFieldDefn(n).name
        pfn.append(name)

## Get field name of shelter layer
sfn = [] #road field name
shelter_field = shelter_lyr.GetLayerDefn()
for n in range(shelter_field.GetFieldCount()) :
        name = shelter_field.GetFieldDefn(n).name
        sfn.append(name)
      
"""
In this cell, we create a dataset for the analysis
The algorithm converts the shapefiles into a graph and a set of dataframes
If we have done this part before, we do not have to do this
"""
### Create a graph from road network
### Create dictionaries for refering node's coordinates

## create empty graph
G = nx.Graph()

## Create data frame for saving road information
road_df = pd.DataFrame(columns=['START_NODE', 'END_NODE', 'COORDINATES', 'LEN', 'HAZARD'])

## Prepare empty dataset to save an information
dict_coorToNum = {} # the dictionary to find a node number from coordinates
dict_numToCoor = {} # the dictionary to find a coordinates from a node number
key = 0 # row of matrix
value = 0 # column of matrix
num = 0

## add node and edge in the enpy graph
for feat in road_lyr : # call features from a road mayer
    geom = feat.geometry() # get a geometry from the feature
    if geom is None :
        continue
    attr = [] #attributes
    l = geom.GetPointCount() # get the number of points of each line
    x_start = geom.GetX(0) # get the first and last points' coordinates of line
    x_end = geom.GetX(l-1)
    y_start = geom.GetY(0)
    y_end = geom.GetY(l-1)
    start = str(x_start)+','+str(y_start) # combine the coordinates to save as string
    end = str(x_end)+','+str(y_end)
    # if the node (coordinates) is new in the matrix, add it in the matrix
    if start not in list(dict_coorToNum.keys()) :
        dict_coorToNum[start] = key # and save the information in the dictionaries
        dict_numToCoor[key] = start
        key += 1 # and add the key number
    if end not in list(dict_coorToNum.keys()) :
        dict_coorToNum[end] = key
        dict_numToCoor[key] = end
        key += 1
    length = feat.GetField('LEN')
    hazard = feat.GetField('HAZARD')
    f_id = feat.GetField('NUM')
    # add the edge in the matrix
    G.add_edge(dict_coorToNum[start], dict_coorToNum[end], fid = f_id, LEN = length, HAZARD = hazard, 
               START= (y_start, x_start), END=(y_end, x_end))
    # get the coordinates of all points of line feature
    geom_list = [] 
    for i in range(geom.GetPointCount()) : # call the coordiantes and concatnate them as a string to save
        geom_list.append(str(geom.GetY(i)) + ',' + str(geom.GetX(i)))
    geoms = '|'.join(geom_list)
    # add coordinates information in the data frame
    row = [dict_coorToNum[start], dict_coorToNum[end], geoms, length, hazard]
    road_df.loc[num] = row
    if num % 500 == 0 :
        print(row)
    num += 1
    
"""
In this cell, we save the results of above cell
"""
## Save the dictionaris as json files
json_dict_coorToNum = json.dumps(dict_coorToNum)
f = open('.json', 'w')
f.write(json_dict_coorToNum)
f.close()

json_dict_numToCoor = json.dumps(dict_numToCoor)
f = open('or.json', 'w')
f.write(json_dict_numToCoor)
f.close()

road_df.to_json('f.json')

## Save the graph into a json file
js_graph = json.dumps(json_graph.node_link_data(G))
f = open('.json', 'w')
f.write(js_graph)
f.close()

"""
Notice!
If we already have dataset as jsonfiles, we just read these files
"""
# read data for analysis
dict_coorToNum = json.load(open(
    '.json'))
dict_numToCoor = json.load(open(
    '.json'))
js_G = json.load(open(
    '.json', "r"))
G = json_graph.node_link_graph(js_G)

"""
In this cell, we convert the shapefiles into lists of start and end nodes
The data saves their coordinates, id, and population number, and capacity area
"""
## Get start node information (pop)
pop_point = []
for feat in pop_lyr :
    geom = feat.geometry()
    x = geom.GetX()
    y = geom.GetY()
    coor = str(x)+','+str(y)
    pid = int(feat.GetField('PID'))
    pop = feat.GetField('TMST_20_su')
    pop_point.append([coor, pid, pop])   

## Get end node information (shelter)
shel_point = []
for feat in shelter_lyr :
    geom = feat.geometry()
    x = geom.GetX()
    y = geom.GetY()
    coor = str(x)+','+str(y)
    sid = int(feat.GetField('SID'))
    cap = feat.GetField('AREA')
    shel_point.append([coor, sid, cap])
    
"""
In this module, we assign population to shelter by the shortest path.
We ignore shelter capacity in this module.
However, if road hazard of the shortest path is longer than the original shortest path,
we assign next routes for population.
"""

### Create an expty dataframe
hazard_df = pd.DataFrame(columns=['POP_ID', 'SHELTER_ID', 'POP_NODE', 'SHELTER_NODE', 
                                    'POP', 'CAP', 'LEN', 'HAZARD'])

## Create shapefile
driver = ogr.GetDriverByName('ESRI Shapefile')
data_source = driver.CreateDataSource('.shp')
create_lyr = data_source.CreateLayer('hazard_path', road_lyr.GetSpatialRef(), ogr.wkbMultiLineString)
data_source.Destroy()

## Create shortest path as linestring
## read shapefile
path_ds = ogr.Open('.shp', 1)
path_lyr = path_ds.GetLayer('hazard_path')
path_defn = path_lyr.GetLayerDefn()
print(path_lyr.GetGeomType() == ogr.wkbLineString)

## set field
field_name = ['POP_ID', 'SHEL_ID', 'POP_NODE', 'SHEL_NODE', 'POP', 'CAP', 'LEN', 'HAZARD']
path_lyr.CreateField(ogr.FieldDefn('POP_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('CAP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('LEN', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('HAZARD', ogr.OFTReal))

## Start creating matrix and line features
num = 0
error = []
for pop in pop_point :
    ## load population information
    pop_node = dict_coorToNum[pop[0]]
    pop_id = pop[1]
    pop_num = pop[2]
    shelters = {} # set an empty dictionary to assign the population
    for shelter in shel_point :
        ## load shelter information
        shelter_node = dict_coorToNum[shelter[0]]
        shelter_id = shelter[1]
        shelter_cap = shelter[2]
        ## calculate the shortest path
        try :
            hazard_len = nx.shortest_path_length(G, pop_node, shelter_node, weight='HAZARD')
            ## save the results in the dictionaty
            shelters[hazard_len] = [shelter_id, shelter_node, shelter_cap]
        except :
            ## if the algorithm cannot find the shortest path, it saves the results and skip the process
            print('error: ' + str(pop_id) + '/' + str(shelter_id))
            error.append([pop_id, shelter_id])
    if len(shelters) == 0 :
        continue
    else :
        ## find the shelter that has the shortest distance from the population
        lists = list(shelters.keys())
        short_shelter = shelters[min(lists)]
        ## re-calculate the shortest path
        shortest_path = nx.dijkstra_path(G, pop_node, short_shelter[1], weight='HAZARD')
        shortest_hazard = nx.shortest_path_length(G, pop_node, short_shelter[1], weight='HAZARD')
        shortest_len = 0
        for i in range(0, len(shortest_path)-1) :
            shortest_len += G[shortest_path[i]][shortest_path[i+1]]['LEN']
        ## save the results in the dataframe
        row = [pop_id, short_shelter[0], pop_node, short_shelter[1], pop_num, 
               short_shelter[2], shortest_len, shortest_hazard]
        hazard_df.loc[num] = row
        ## create line features of the shortest path
        geom = ogr.Geometry(ogr.wkbLineString)
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(short_shelter[0]))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(short_shelter[1]))
        feat.SetField('POP', pop_num)
        feat.SetField('CAP', short_shelter[2])
        feat.SetField('LEN', shortest_len)
        feat.SetField('HAZARD', shortest_hazard)
        feat.SetGeometry(geom)
        path_lyr.CreateFeature(feat)
        num += 1
        if num % 500 == 0 :
            print(num)
            
 ## close path
path_ds.Destroy()
## save the results
hazard_df.to_json('.json')
hazard_df.to_csv('y.csv')
