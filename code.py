import pandas as pd
import numpy as np
import math
import rdflib
from rdflib import Literal, BNode, URIRef, Graph, Namespace
from rdflib.namespace import RDF, OWL, RDFS, FOAF, XSD, XMLNS

### Storing all the data on pandas dataframe objects. This makes it easier to manipulate.
indInfo = pd.read_excel('contact_dataset.xlsx', sheet_name='Individuals Personal Info', index_col='Individual')
testResults = pd.read_excel('contact_dataset.xlsx', sheet_name='Covid Test Results', index_col='Individual')
vaxData = pd.read_excel('contact_dataset.xlsx', sheet_name='Vaccination Data', index_col='Individual')
contact = pd.read_excel('contact_dataset.xlsx', sheet_name='Individuals Contact Tracing', index_col='Individual')
mortality = pd.read_excel('contact_dataset.xlsx', sheet_name='COVID Mortality Data', index_col='Individual')

### Initialize a knowledge graph
g = Graph()

#Our Ontology
cvdo = rdflib.Namespace('http://www.semanticweb.org/abdel/ontologies/2021/10/COVID-19-Ontology#')

#Bind prefixes to ontologies used in the graph
g.bind("cvdo", cvdo)
g.bind("foaf", FOAF)
g.bind("rdf", RDF)

# Create Person instances and add their attributes
for i in indInfo.index:
    g.add((cvdo[i], RDF.type, FOAF.Person))     ### Class definition
    g.add((cvdo[i], cvdo.age, Literal(indInfo['Age'].loc[i], datatype = XSD.integer)))  ### age data
    g.add((cvdo[i], cvdo.gender, Literal(indInfo['Gender'].loc[i])))   ### gender data

# replacing NaN values with zeros to help with reasoning (Household database)
hhMembers = indInfo['Household Members'].str.split(', ', expand=True).fillna(0)
# create the list of households from the data
hhList = []
for i in hhMembers.index: # iterating by instance
    a = [i] # array with individual as index
    for j in hhMembers.columns: # iterating by column
        if hhMembers[j].loc[i] != 0:
            a.append(hhMembers[j].loc[i]) # adding household member
    a = sorted(a)
    hhList.append(a)

# using sets allows us to easily remove duplicates from the households list
hhList = sorted(set(map(tuple, hhList)))
# adding household information
hhNames = []
for i in range(len(hhList)):
    hh = 'H'+str(i+1)
    hhNames.append(hh)
    g.add((cvdo[hh], RDF.type, cvdo.Household)) # initialize an instance of household
    for j in hhList[i]:
        g.add((cvdo[j], cvdo.memberOf, cvdo[hhNames[i]]))   # add member attribute to person
        g.add((cvdo[hhNames[i]], cvdo.hasMember, cvdo[j]))  # add hasMember attribute to household

        address = Literal(indInfo['City of Residence'].loc[j])  # add the city of residence or "address"
        g.add((cvdo[hhNames[i]], cvdo.residesAt, address))


# adding vaccination information
# same as before we replace NaN values with zeros
vaxData = vaxData.fillna(0)
n = 1
for i in vaxData.index: # iterate by individual
    if vaxData['Vaccine Type'].loc[i] != 0: # apply simple logic
        vax = 'V' + str(n) # name for vaccine instance
        g.add((cvdo[vax], RDF.type, cvdo.COVIDVaccine)) # create vaccine instance
        vaxDate = Literal(vaxData['Vaccination Date'].loc[i], datatype = XSD.dateTime) # vaccination date
        vaxType = Literal(vaxData['Vaccine Type'].loc[i])   # vaccine type
        g.add((cvdo[vax], cvdo.vaccinationDate, vaxDate)) # adding vaccination date and type
        g.add((cvdo[vax], cvdo.vaccineType, vaxType))

        g.add((cvdo[i], cvdo.received, cvdo[vax])) # add a received attribute to the person
        n += 1

# adding COVID test data
n = 1
for i in testResults.index: # iterate by person
    test = 'T' + str(n) # name for test instance
    testDate = Literal(testResults['Test Date'].loc[i], datatype = XSD.dateTime) # test date
    resultDate = Literal(testResults['Result Date'].loc[i], datatype = XSD.dateTime)    # result date
    result = Literal(testResults['Result'].loc[i]) # actual result
    g.add((cvdo[test], RDF.type, cvdo.COVIDTest))  # make instance of test
    g.add((cvdo[test], cvdo.testDate, testDate))    # add test date
    g.add((cvdo[test], cvdo.resultDate, resultDate))    # add result date
    g.add((cvdo[test], cvdo.result, result))    # add test result data
    g.add((cvdo[i], cvdo.tookTest, cvdo[test])) # add a tookTest attribute to person
    n += 1

# adding contact tracing data
n = 1
for i in contact.index: # iterate by individual
    contPers = contact['Contacted person'].loc[i]   #   Contacted person
    cont = 'C' + str(n) #   Instance name for contact event
    contDate = Literal(contact['Date'].loc[i], datatype = XSD.dateTime) # date of contact
    g.add((cvdo[cont], RDF.type, cvdo.ContactEvent))    #   create instance of contact event
    g.add((cvdo[cont], cvdo.hasAgent, cvdo[contPers]))  #   add contacted person using hasAgent attribute
    g.add((cvdo[cont], cvdo.timeOfContact, contDate))   #   add the time of contact
    g.add((cvdo[i], cvdo.hadContact, cvdo[cont]))       #   add hadContact attribute to person
    n += 1

# adding mortality data
n = 1
for i in mortality.index:
    dDay = Literal(mortality['Date of Death'].loc[i], datatype = XSD.dateTime)  #   Date of death
    g.add((cvdo[i], cvdo.dateOfDeath, dDay))    #   add the date of death
    n += 1

G = g.serialize(destination='data.ttl', format='turtle') #   Store the turtle file in the pwd
