#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 29 14:14:51 2017

@author: Simon
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 20 17:44:20 2017

@author: Simon J Moreno
"""
import os
import math
import random
import numpy as np
import scipy.stats as stats
import networkx as nx
from itertools import islice
import time
import multiprocessing
import threading
import pandas as pd
import csv
import os.path

numSamples = 1E4
numSamplesTrasient = 1E3
writeAiFile = True

numNodes = 14

redNSFNet = {
        0:{1:{'distance':1100},2:{'distance':1600},7:{'distance':2800}},
        1:{0:{'distance':1100},2:{'distance':600},3:{'distance':1000}},
        2:{0:{'distance':1600},1:{'distance':600},5:{'distance':2000}},
        3:{1:{'distance':1000},4:{'distance':600},10:{'distance':2400}},
        4:{3:{'distance':600},5:{'distance':1100},6:{'distance':800}},
        5:{2:{'distance':2000},4:{'distance':1100},9:{'distance':1200},12:{'distance':2000}},
        6:{4:{'distance':800},7:{'distance':700}},
        7:{0:{'distance':2800},6:{'distance':700},8:{'distance':700}},
        8:{7:{'distance':700},9:{'distance':900},11:{'distance':500},13:{'distance':500}},
        9:{5:{'distance':1200},8:{'distance':900}},
        10:{3:{'distance':2400},11:{'distance':800},13:{'distance':800}},
        11:{8:{'distance':500},10:{'distance':800},12:{'distance':300}},
        12:{5:{'distance':2000},11:{'distance':300},13:{'distance':300}},
        13:{8:{'distance':900},10:{'distance':800},12:{'distance':300}}
        } 

numWavelengths = 8
numFibresLinks = 1

tiempoMedioServicio = 60


numMaxPath = 5


random.seed(7)


# Global Variables

tiempoMedioEntrePeticiones = 0.0
blockingRatio = []
simTime = 0.0
eventList = []
grafo = nx.DiGraph(redNSFNet)
linksInNetwork=nx.edges(grafo)
channelStatus = np.zeros((len(linksInNetwork),numWavelengths),bool)
kShortestPaths = []
df = pd.DataFrame()
datos = []













def GenerarListaCaminos():
    
  
    #print(nx.shortest_path(grafo, source=4, target=13, weight='distance'))
    #a = nx.shortest_simple_paths(grafo, source=4, target=13)
    #for i in a:
    #    print(i)
   
    global kShortestPaths
    global grafo
    global singleLinkGraph
    

    singleLinkGraph = nx.DiGraph()
    for n, nbrs in grafo.adjacency():
        for nbr, edict in nbrs.items():
            singleLinkGraph.add_edge(n, nbr)
    
    kShortestPaths = []
    
    for source in range(numNodes):
        auxiliar = []
        for destination in range(numNodes):
            auxiliardos = []

            for pathNodes in k_shortest_paths(singleLinkGraph, source, destination, numMaxPath):
                for numFibre in range(numFibresLinks):

                    path = []
                    
                    for pathNode in range(len(pathNodes)-1):
                        for link in range(len(linksInNetwork)):
                            if ((linksInNetwork[link][0]==pathNodes[pathNode]) and (linksInNetwork[link][1]==pathNodes[pathNode+1]) and (linksInNetwork[link][2] == numFibre)):
                                path.append(link)
                                break
                    auxiliardos.append(path)

            auxiliar.append(auxiliardos)

        kShortestPaths.append(auxiliar)        


#    Si queremos Shortes path con distancia: k_shortest_paths(grafo, 4, 13, 5,'distance'):


def k_shortest_paths(G, source, target, k, weight=None):
    return list(islice(nx.shortest_simple_paths(G, source, target,weight), k))


    
def GenerarPeticion():
    global tiempoMedioEntrePeticiones
    global simTime
    global eventList
    global channelStatus 
    global df
    global blockingRatio
    global datos
    global wr
    
    if len(eventList) > 0: # La primera vez no es 0
        eventList.pop(0)
    
    tiempoSiguientePeticion = simTime + random.expovariate(1/tiempoMedioEntrePeticiones)
    
    siguientePeticion = {'tiempo' : tiempoSiguientePeticion, 'tipo' : 'Nueva_Peticion'}
        
    for i in range(len(eventList)):
        
        if eventList[i]['tiempo'] > siguientePeticion['tiempo']:
            eventList.insert(i,siguientePeticion)
            break
        
        if i == (len(eventList)-1):
            eventList.append(siguientePeticion)
            
    if len(eventList) == 0:
        eventList.append(siguientePeticion)
    
    
    sourceNode = random.randint(0,numNodes-1)
    destinationNode = random.randint(0,numNodes-2)
    if(destinationNode>=sourceNode):
        destinationNode += 1
    tiempoEliminarLightpath = simTime + random.expovariate(1/tiempoMedioServicio)
            
    #print("Crear nueva peticion: ", sourceNode, destinationNode, tiempoEliminarLightpath, tiempoSiguientePeticion)
    
    features = [sourceNode] + [destinationNode] + list(channelStatus.flatten())
    
    resultRWA = AurExhaustive(sourceNode, destinationNode)
    
    #resultRWA = ShortestPathsFirstFit(sourceNode, destinationNode)
    #print(resultRWA)
    
    if resultRWA[0] == True:
        
        blockingRatio.append(0)
        
        if writeAiFile == True:
            muestra = [resultRWA[1]] + features
            muestra = np.array(muestra, dtype = np.int16)
            wr.writerow(muestra)

        borradoLightpath = {'tiempo' : tiempoEliminarLightpath, 'tipo' : 'Eliminar_Lightpath', 'path' : resultRWA[2], 'wavelength': resultRWA[1]}
        
        for i in range(len(eventList)):
            if eventList[i]['tiempo'] > borradoLightpath['tiempo']:
                eventList.insert(i,borradoLightpath)
                break
            
            if i == (len(eventList)-1):
                eventList.append(borradoLightpath)

    else:
        blockingRatio.append(1)



def EliminarLightpath():
    global eventList
    
    lightpath = eventList.pop(0)
    
    for link in lightpath['path']:
        channelStatus[link][lightpath['wavelength']] = False    
    






def AurExhaustive(sourceNode, destinationNode):

    global singleLinkGraph
    global grafo
    
    pathFound = False
    path = []
    wavelength = -1
    
    #print(sourceNode, destinationNode)
    #print(kShortestPaths[sourceNode][destinationNode])

    tablaDistanceLayer = np.inf*np.ones(shape = (numFibresLinks, numWavelengths))
    
    #print("Source->Destination: " + str(sourceNode) + " -> " + str(destinationNode))
    
    for numFibre in range(numFibresLinks):
        for w in range(numWavelengths):
            for link in range(len(linksInNetwork)):
                if linksInNetwork[link][2] == numFibre:
                    if channelStatus[link][w] == True:
                        singleLinkGraph.remove_edge(linksInNetwork[link][0], linksInNetwork[link][1])
                        #print("Borro: " + str(linksInNetwork[link][0]) + " - " + str(linksInNetwork[link][1]))
            try:
                distance = nx.shortest_path_length(singleLinkGraph, sourceNode, destinationNode)
                tablaDistanceLayer[numFibre][w] = distance
                #print("Fibra: " + str(numFibre) + ". W = " + str(w) + ". Distancia: " + str(distance) + "\n")
            except nx.NetworkXNoPath:
                tablaDistanceLayer[numFibre][w] = np.inf
            
            for link in range(len(linksInNetwork)):
                if linksInNetwork[link][2] == numFibre:
                    if channelStatus[link][w] == True:
                        singleLinkGraph.add_edge(linksInNetwork[link][0], linksInNetwork[link][1])
                        
    #print(tablaDistanceLayer)
    
    if tablaDistanceLayer.min() < np.inf :
        
        filaUno = tablaDistanceLayer[0]
        
        pathFound = True
        
        #minPosition = np.unravel_index(tablaDistanceLayer.argmin(), tablaDistanceLayer.shape)
        #wavelength = minPosition[1]
        
        wavelength = tablaDistanceLayer.argmin()
        minPosition = 0
        #print(tablaDistanceLayer.min())
        #print(minPosition)
        
        
        for link in range(len(linksInNetwork)):
            if linksInNetwork[link][2] == minPosition:
                if channelStatus[link][wavelength] == True:
                    singleLinkGraph.remove_edge(linksInNetwork[link][0], linksInNetwork[link][1])
                    #print("Borro: " + str(linksInNetwork[link][0]) + " - " + str(linksInNetwork[link][1]))
     
        pathInNodes = nx.shortest_path(singleLinkGraph, sourceNode, destinationNode)
        #print(pathInNodes)
        
        for link in range(len(linksInNetwork)):
            if linksInNetwork[link][2] == minPosition:
                if channelStatus[link][wavelength] == True:
                    singleLinkGraph.add_edge(linksInNetwork[link][0], linksInNetwork[link][1])
                    #print("Creo: " + str(linksInNetwork[link][0]) + " - " + str(linksInNetwork[link][1]))

        
                    
        for pathNode in range(len(pathInNodes)-1):
            for link in range(len(linksInNetwork)):
                if ((linksInNetwork[link][0]==pathInNodes[pathNode]) and (linksInNetwork[link][1]==pathInNodes[pathNode+1]) and (linksInNetwork[link][2] == minPosition)):
                    path.append(link)
                    break
                
        for link in path:
            if channelStatus[link][wavelength] == False:
                channelStatus[link][wavelength] = True
            else:
                print("ERROR EN EL CAMINO\n")
        #print(path)
    return(pathFound, wavelength, path)
    



def ShortestPathsFirstFit(sourceNode, destinationNode):

    
    #print(sourceNode, destinationNode)
    #print(kShortestPaths[sourceNode][destinationNode])
    path = []
    wavelength = -1
    for w in range(numWavelengths):
        for path in kShortestPaths[sourceNode][destinationNode]:
            pathFound = True
            for link in path:
                if channelStatus[link][w] == True :
                    pathFound = False
                    break
                
            if pathFound == True :
                wavelength = w
                #print(sourceNode,destinationNode,path, w)
                for link in path:
                    if channelStatus[link][w] == False:
                        channelStatus[link][w] = True 
                    else:
                        print("ERROR EN EL CAMINO\n")
                break
            
        if pathFound == True :
            break
    
    return(pathFound, wavelength, path)    


def getStatistics():
        
    samples = np.asarray(blockingRatio[int(numSamplesTrasient):])
    #blockingRatio = blockingRatio[numSamplesTransient,:]
    validSamples = []
    numBlocks = 1E3
    numSamplesBlock = len(samples)/numBlocks
    
    for i in range(int(numBlocks)):
        block = np.asarray(samples[int(numSamplesBlock*i):int(numSamplesBlock*(i+1))])
        validSamples.append(block.mean())
    
    validSamples = np.asarray(validSamples)
    sampleMean = validSamples.mean()
    
    z_critical = stats.norm.ppf(q = 0.975)
    samples_stdev = validSamples.std()
    marginError = z_critical * (samples_stdev/math.sqrt(len(validSamples)))
    
    
    
    
    print("Carga ",load, "= ", sampleMean, " +- ", marginError)

    resultFile = open("result.csv",'a')
    wr = csv.writer(resultFile)
    muestra = ["AUR-EXHAUSTIVE"] + [load] + [sampleMean] + [marginError]
    wr.writerow(muestra)
    resultFile.close()


   
def simulation(load):
    
   

    print("\n\nPID: %s, Process Name: %s, Thread Name: %s\n\n" % (os.getpid(),multiprocessing.current_process().name,threading.current_thread().name))

 
    numSamplesTotal = numSamples + numSamplesTrasient
    
    
    global grafo
    global channelStatus 
    global linksInNetwork  
    global numNodes
    global numWavelengths
    global tiempoMedioServicio
    global tiempoMedioEntrePeticiones 
    global simTime
    global eventList
    global blockingRatio
    global df
    global resultFile 
    global wr
    

    
    # Create graph multifibre and directed        
    grafo = nx.MultiDiGraph()
    
    # Add nodes
    nodes_name = list(redNSFNet.keys())
    grafo.add_nodes_from(nodes_name)
     
    # Add fibres
    for source in nodes_name:
        destinations = list(redNSFNet[source].keys())
        for destination in destinations:
            distan = redNSFNet[source][destination]['distance']
            for fibre in range(numFibresLinks):
                grafo.add_edge(source, destination, distance = distan)
    
    
    linksInNetwork = list(grafo.edges)
    channelStatus = np.zeros((len(linksInNetwork),numWavelengths))
    #nx.draw_networkx(grafo, with_labels=True, font_weight='bold', node_size = 1000)

    if writeAiFile == True:
        fileExists = os.path.isfile("output.csv") 
        resultFile = open("output.csv",'a')
        wr = csv.writer(resultFile)
        
        if fileExists == False:
            dfColumnsNames = ['wavelength', 'source', 'destination']
            
             
            for link in linksInNetwork:
                for w in range(numWavelengths):
                    dfColumnsNames += [str(link[0]) + '-' + str(link[1]) + '-' + str(w)]
    
            wr.writerow(dfColumnsNames)
    


    
    GenerarListaCaminos() # Generar lista caminos mas cortos
    print(kShortestPaths)
    
  
    
    global tiempoMedioEntrePeticiones 
    
    tiempoMedioEntrePeticiones = tiempoMedioServicio/(numNodes*(numNodes-1)*load)
     
    
    GenerarPeticion()
    
    anterior = 0
    #print(eventList)
    
    while len(blockingRatio) < numSamplesTotal :
        
        if (len(blockingRatio) % 2E3 == 0) and (len(blockingRatio) != anterior) :
            print('Tiempo de simulación: ' + str(simTime) + '. Número de muestras: ' + str(len(blockingRatio)))
            anterior = len(blockingRatio)
        
        simTime = eventList[0]['tiempo']
        #print("\n\nTiempo actual: ",simTime)
        #print("Lista eventos:")
        #print(os.getpid(),len(eventList))
        
        evento = eventList[0]
        
        if evento['tipo'] == 'Nueva_Peticion':
            GenerarPeticion()
        
        if evento['tipo'] == 'Eliminar_Lightpath':
            EliminarLightpath()    
 
    getStatistics()


    if writeAiFile == True:
        resultFile.close()




def reiniciar():
    
    global blockingRatio
    global simTime
    global eventList
    
    blockingRatio = []    
    simTime = 0.0    
    eventList = []



    


if __name__ == "__main__":
    
    
    #loads = [1.5, 1.4, 1.3, 1.2, 1.1, 1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
    loads = [0.5]
    #loads = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    
    for load in loads:
        reiniciar()
        simulation(load)
    
    

