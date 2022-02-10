from os import remove
import sqlite3
import codecs
from numpy import append
import pygame,pygame.freetype,pygame.gfxdraw
import pygame,pygame.freetype,pygame.gfxdraw
import sys, traceback
#from pygame.locals import K_ESCAPE
import math


make_data = True
#make_data = False

def line_len(pt1,pt2):
    return round(math.sqrt( pow(pt1[0]-pt2[0],2) + pow(pt1[1]-pt2[1],2)),3)

#######################################################################################
#
#   LOAD DATA FROM TEXT FILE
#
#######################################################################################

try:
    con = sqlite3.connect('map.db')
    cur = con.cursor()

    # read data from text file
    if make_data:
        init = ["drop table if exists `names`;",
        "CREATE TABLE `names` (`id` INTEGER PRIMARY KEY,`name` TEXT);",
        "drop table if exists `coords`;",
        "CREATE TABLE `coords` (`id` INTEGER,`order` INTEGER,`x` REAL,`y` REAL);",
        ]
        insert = [
        "insert into `names` (`id`,`name`) VALUES({},'{}');",
        "insert into `coords` (`id`,`order`,`x`,`y`) VALUES({},{},{},{});",
        ]
        closeup = ["CREATE INDEX `street_id` ON `coords` (id ASC);"]
        for sql in init:
            cur.execute(sql)
        con.commit()

        count = 0
        with codecs.open('map2.txt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # print ("#{} {}".format(count,line))
                a = line.split("\t")
                
                # street name
                sql = insert[0].format(count,a[0])
                cur.execute(sql)
                con.commit()

                #coords
                pt=0
                for cc in range(1,len(a)):
                    coords = a[cc].split(",")
                    sql = insert[1].format(count,pt,coords[0],coords[1])
                    cur.execute(sql)
                    
                    pt+=1
                count+=1
        con.commit()
        f.close()   
        
        # создаем ключи
        for sql in closeup:
            cur.execute(sql)
        con.commit() 
        del pt,a,cc,sql,count,line,coords,init,closeup,insert,f
        print('-------------------------------------------------')        
        print('База загружена из текстового файла')
        

    del make_data


    #######################################################################################
    #
    #   PARSE DATA: MAKE NODEs AND GRAPHs
    #
    #######################################################################################

    nodes_count = -1
    nodes = [] 
    graph = [] 

    # 5/5
    HOUSE_DENSITY = 5
    TRESHOLD = 5
  
    cur.execute("select count(distinct id) from coords;")
    rows = cur.fetchall()
    cnt = rows[0][0]
    print('-------------------------------------------------')        
    print('Найдено в базе улиц: {}'.format(cnt))
    for street_idx in range(cnt):
        cur.execute("select x,y from coords where id={};".format(street_idx))
        segments = cur.fetchall()   
        nodes_count+=1

        # сохраняем первую точку первого сегмента
        nodes.append({"street":street_idx,"pos":[segments[0][0],segments[0][1]],"con":{}})
        
        for segment_idx in range(1,len(segments)):
            
            
            # находим длину сегмента
            l=line_len([segments[segment_idx-1][0],segments[segment_idx-1][1]],[segments[segment_idx][0],segments[segment_idx][1]])
            
            # вычисляем, сколько у нас влезает "домов" на этот сегмент
            house_per_segment = (int)(l / HOUSE_DENSITY)
            
            for sub in range(1,house_per_segment+1):
                # находим координты этого дома
                nx = round(segments[segment_idx-1][0] + (segments[segment_idx][0] - segments[segment_idx-1][0]) / house_per_segment * sub,3)
                ny = round(segments[segment_idx-1][1] + (segments[segment_idx][1] - segments[segment_idx-1][1]) / house_per_segment * sub,3)
                
                # заносим его в ноды
                nodes.append({"street":street_idx,"pos":[nx,ny],"con":{}})
                nodes_count+=1

                # добавляем граф, с длиной
                sub_len = line_len( nodes[nodes_count-1]["pos"], [nx,ny])
                graph.append({"start":nodes_count-1,"end":nodes_count,"len":sub_len,"type":0})
           

    del cnt,l,nx,ny,rows,street_idx,segment_idx,house_per_segment,sub,sub_len,segments,nodes_count,con,cur
  
    graph_count = len(graph)
    print('Создано нодов: {}'.format(len(nodes)))
    print('Создано графов: {}'.format(graph_count))


    #######################################################################################
    #
    #   ADD NEIGHBOURS TO NODES 
    #
    #######################################################################################

    for g in graph:
        n = nodes[g["start"]]
        k = n["con"].keys() 
        if not(g["end"] in k):
            n["con"][g["end"]] = g["len"]

        n = nodes[g["end"]]
        k = n["con"].keys() 
        if not(g["start"] in k):
            n["con"][g["start"]] = g["len"]
    del n,k,g

    #######################################################################################
    #
    #   ADD MISSING GRAPHS
    #
    #######################################################################################
    def graph_exists(graph,i,j):
        for g in graph:
            if (((g["start"]==i) and (g["end"]==j)) or ((g["start"]==j) and (g["end"]==i))):
                return True
        return False

    
    for ns in range(len(nodes)):
        for nd in range(len(nodes)):
            # если разные улицы
            if (nodes[ns]["street"] != nodes[nd]["street"]):
                # если длина подходит
                l = line_len(nodes[ns]["pos"],nodes[nd]["pos"]) 
                if l<=TRESHOLD:
                    # print("- connect {}-{}, len: {}".format(ns,nd,l))   
                    k = nodes[ns]["con"].keys() 
                    if not(nd in k):
                        nodes[ns]["con"][nd] = l
                    k = nodes[nd]["con"].keys() 
                    if not(ns in k):
                        nodes[nd]["con"][ns] = l
                    if not graph_exists(graph,ns,nd):
                        graph.append({"start":ns,"end":nd,"len":l,"type":1})   

    print('Добавлено графов: {}'.format(len(graph)-graph_count))
    del graph_count,k,ns,nd,l
    
    W = 1000
    H = 700
    MARGIN = 50

    # calculate map map borders
    minx = maxx = nodes[0]["pos"][0]
    miny = maxy = nodes[0]["pos"][1]
    for i in range(1,len(nodes)):
        if (nodes[i]["pos"][0]>maxx): maxx = nodes[i]["pos"][0]
        if (nodes[i]["pos"][0]<minx): minx = nodes[i]["pos"][0]
        if (nodes[i]["pos"][1]>maxy): maxy = nodes[i]["pos"][1]
        if (nodes[i]["pos"][1]<miny): miny = nodes[i]["pos"][1]
    
    # calculate map dimensions
    kx = (W-MARGIN*2) / (maxx - minx)
    ky = (H-MARGIN*2) / (maxy - miny)
    k=kx if kx<ky else ky
    del kx,ky,i

    def geo2screen(pt): 
        global k,minx,miny,H
        x = pt[0]-minx
        y = pt[1]-miny
        x *= k
        y *= k
        x += MARGIN
        y += MARGIN
        y = H - y # flip vertical
        return [x,y]
    
    def screen2geo(pt): 
        global k,minx,miny,H
        y = H - pt[1]
        x = pt[0] - MARGIN 
        y = y - MARGIN 
        x /= k
        y /= k
        x += minx
        y += miny
        return [x,y]

    
    def reconstruct_path(cameFrom, current):
        total_path = [current]
        while current in cameFrom.keys():
            current = cameFrom[current]
            total_path.append(current)
        return total_path
    
    # h is the heuristic function. h(n) estimates the cost to reach goal from node n.
    def A_Star(start, goal):
        global nodes

        openSet = [start]
        cameFrom = {}

        # For node n, gScore[n] is the cost of the cheapest path from start to n currently known.
        gScore = []
        fScore = []
        # For node n, fScore[n] = gScore[n] + h(n). fScore[n] represents our current best guess as to
        # how short a path from start to finish can be if it goes through n.
        
        for i in range(len(nodes)):
            gScore.append(float('inf'))  
            fScore.append(float('inf'))    
        
        gScore[start] = 0
        fScore[start] = line_len( nodes[start]["pos"], nodes[goal]["pos"])

        while len(openSet)>0:
            # This operation can occur in O(1) time if openSet is a min-heap or a priority queue
            #current = the node in openSet having the lowest fScore[] value
            current = openSet[0]
            min_val = fScore[current]
            for i in openSet:
                if fScore[current] < min_val:
                    current = i
                    min_val = fScore[current]

            
            if current == goal:
                return reconstruct_path(cameFrom, current)

            openSet.remove(current)
            for neighbor in nodes[current]["con"]:
                # d(current,neighbor) is the weight of the edge from current to neighbor
                # tentative_gScore is the distance from start to the neighbor through current
                tentative_gScore = gScore[current] + nodes[current]["con"][neighbor]
                if tentative_gScore < gScore[neighbor]:
                    # This path to neighbor is better than any previous one. Record it!
                    cameFrom[neighbor] = current
                    gScore[neighbor] = tentative_gScore
                    fScore[neighbor] = tentative_gScore + line_len( nodes[neighbor]["pos"], nodes[goal]["pos"]) 
                    if neighbor not in openSet:
                        openSet.append(neighbor)

        # Open set is empty but goal was never reached
        return []
    
    def get_nearest_node(x,y):
        global nodes
        idx = 0
        min_len = line_len( nodes[0]["pos"],[x,y])
        for n in range(1,len(nodes)):
                l = line_len( nodes[n]["pos"],[x,y])
                if (l<min_len):
                    idx = n
                    min_len = l
        return idx
                

    def calc_path(path):
        global nodes
        path["start_geo"] = screen2geo(path["start_screen"])
        path["end_geo"] = screen2geo(path["end_screen"])
        path["start_node"] = get_nearest_node(path["start_geo"][0],path["start_geo"][1])
        path["end_node"] = get_nearest_node(path["end_geo"][0],path["end_geo"][1])
        path["nodes"] = A_Star(path["start_node"],path["end_node"])


    FPS = 10
    running = True
    clock = pygame.time.Clock()
    
    CLR_BG = (0x14,0x1E,0x27)
    CLR_LINE = (0x004ee1)
    CLR_ADDED = (0xffff00)
    CLR_POINTS = (0xff483d)
    CLR_PTS = (0x3bd200)
    CLR_PTE = (0xd20000)
    CLR_PATH = (0x3bd233)
    CLR_FNT = (0xFF,0xFF,0x00)

    path = {
    "start_screen": [100,100],
    "end_screen": [500,500]
    }
    
    calc_path(path)

    try:
        pygame.init()
        pygame.font.init() 
        fnt = pygame.freetype.Font("app.ttf", 16)
        pygame.display.set_caption("Васька")
        surf_act = pygame.display.set_mode((W, H))
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: sys.exit()
                elif event.type == pygame.KEYDOWN: 
                    if (event.key == 27):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN: 
                    if (event.button == 1): 
                        path["start_screen"] = event.pos
                        calc_path(path)
                    elif (event.button == 3): 
                        path["end_screen"] = event.pos
                        calc_path(path)




            # BG
            surf_act.fill(CLR_BG) 
            # рисуем графы
            for g in graph:
                pt0 = geo2screen( nodes[g["start"]]["pos"] )
                pt1 = geo2screen( nodes[g["end"]]["pos"] )
                # разные цвета для стандартных/добавленных графов
                if (g["type"]==0): pygame.draw.line(surf_act,CLR_LINE , pt0, pt1, 1)
                else :             pygame.draw.line(surf_act,CLR_ADDED, pt0, pt1, 1)
            # рисуем домики
            i = 0
            for n in nodes:
                pt = geo2screen( n["pos"] )
                pygame.draw.circle(surf_act, CLR_POINTS, pt, 1, 0)
                #fnt.render_to(surf_act, (pt[0]+15,pt[1]-15), str(i), CLR_FNT)
                i += 1
            
            
            
            pygame.draw.line(surf_act,CLR_PATH, 
            geo2screen(nodes[path["start_node"]]["pos"]),
            path["start_screen"],
            1)
            pygame.draw.line(surf_act,CLR_PATH, 
            path["end_screen"],
            geo2screen(nodes[path["end_node"]]["pos"]),
            1)
            
            # draw path
            for i in range(len(path["nodes"])-1):
                
                pygame.draw.line(surf_act,CLR_PATH , 
                geo2screen(nodes[ path["nodes"][i] ] ["pos"]),
                geo2screen(nodes[ path["nodes"][i+1] ] ["pos"]),
                 2)   
            
            # start/end points                
            pygame.draw.circle(surf_act, CLR_PTS, path["start_screen"], 6, 0)
            pygame.draw.circle(surf_act, CLR_PTE, path["end_screen"], 6, 0)

            pygame.display.flip()
            clock.tick(FPS)

    finally:
        pygame.quit()
                

except Exception as e:
    print()
    print("\n=-=-=- ERROR =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")
    e = sys.exc_info()[1]
    print(e.args[0])
    traceback.print_exc()
    print("\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-\n")



