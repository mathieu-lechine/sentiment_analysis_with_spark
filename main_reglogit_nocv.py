from pyspark import SparkContext
import loadFiles as lf
import numpy as np
from random import randint
from  pyspark.mllib.classification import NaiveBayes
from functools import partial
from pyspark.mllib.linalg import SparseVector
from pyspark.mllib.regression import LabeledPoint
#cross validation
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql import SQLContext 
from pyspark.ml.tuning import ParamGridBuilder
from pyspark.ml.tuning import CrossValidator
from pyspark.ml.classification import LogisticRegression
from pyspark.mllib.linalg import Vectors

sc = SparkContext(appName="Simple App")

# my modulus
import loadFilesPartial as lfp
#from my_prediction import createBinaryLabeledPoint


def createBinaryLabeledPoint(doc_class,dictionary):
	words=doc_class[0].strip().split(' ')
	#create a binary vector for the document with all the words that appear (0:does not appear,1:appears)
	#we can set in a dictionary only the indexes of the words that appear
	#and we can use that to build a SparseVector
	vector_dict={}
	for w in words:
		vector_dict[dictionary[w]]=1
	return LabeledPoint(doc_class[1], SparseVector(len(dictionary),vector_dict))
def Predict(name_text,dictionary,model):
	words=name_text[1].strip().split(' ')
	vector_dict={}
	for w in words:
		if(w in dictionary):
			vector_dict[dictionary[w]]=1
	return (name_text[0], model.predict(SparseVector(len(dictionary),vector_dict)))


data,Y=lf.loadLabeled("./data/train")
#data,Y=lfp.loadLabeled("./data/train",1000)
print len(data)
dataRDD=sc.parallelize(data,numSlices=16)

#map data to a binary matrix
#1. get the dictionary of the data
#The dictionary of each document is a list of UNIQUE(set) words 
lists=dataRDD.map(lambda x:list(set(x.strip().split(' ')))).collect()
all=[]
#combine all dictionaries together (fastest solution for Python)
for l in lists:
	all.extend(l)
dict=set(all)
print len(dict)
#it is faster to know the position of the word if we put it as values in a dictionary
dictionary={}
for i,word in enumerate(dict):
	dictionary[word]=i
#we need the dictionary to be available AS A WHOLE throughout the cluster
dict_broad=sc.broadcast(dictionary)
#build labelled Points from data
data_class=zip(data,Y)#if a=[1,2,3] & b=['a','b','c'] then zip(a,b)=[(1,'a'),(2, 'b'), (3, 'c')]
dcRDD=sc.parallelize(data_class,numSlices=16)
#get the labelled points
labeledRDD=dcRDD.map(partial(createBinaryLabeledPoint,dictionary=dict_broad.value))


#cross validation
#create a data frame from an RDD -> features must be Vectors.sparse from pyspark.mllib.linalg
sqlContext = SQLContext(sc)
df = sqlContext.createDataFrame(labeledRDD, ['features','label'])
dfTrain, dfTest = df.randomSplit([0.8,0.2])
dfTrain.show()
#choose estimator and grid
#estima = NaiveBayes()
#grid = ParamGridBuilder().addGrid(5, [0, 2]).build()
lr = LogisticRegression(featuresCol="features", labelCol="label", predictionCol="prediction",maxIter=20)	#choose the model
grid = ParamGridBuilder().addGrid(lr.maxIter, [0, 1]).build()	
#la grille est construite pour trouver le meilleur parametre 'alpha' pour le terme de regularisation du modele: c'est un 'elastic Net'
#max.iter vaut 30 par defaut, on pourrait changer sa valeur
#on va donc essayer 30 valeur entre 0 et 1
#alpha=0 c'est une regularisation L2, 
#alpha=1, c'est une regularisation L1
print "Cross validation debut"

evaluator = MulticlassClassificationEvaluator(predictionCol="prediction", labelCol="label",metricName='precision')	#choose the evaluator
cv = CrossValidator(estimator=lr, evaluator=evaluator) #perform the cross validation and keeps the best value of maxIter
#cvModel = cv.fit(dfTrain)	#train the model on the whole training set
model = lr.fit(dfTrain)
resultat=evaluator.evaluate(model.transform(dfTest))	#compute the percentage of success on test set
print "Pourcentage de bonne classification(0-1): ",resultat

##Train NaiveBayes
#model=NaiveBayes.train(labeledRDD)
##broadcast the model
#mb=sc.broadcast(model)
#
#test,names=lf.loadUknown('./data/test')
#name_text=zip(names,test)
##for each doc :(name,text):
##apply the model on the vector representation of the text
##return the name and the class
#predictions=sc.parallelize(name_text).map(partial(Predict,dictionary=dict_broad.value,model=mb.value)).collect()
#
#output=file('./classifications.txt','w')
#for x in predictions:
#	output.write('%s\t%d\n'%x)
#output.close()

# Ceci est un bout de code qu'il faut coller a la fin du script
# qui entraine le modele.
# Cela va creer un fichier texte 'sauvegarde_MYMODEL' (a renommer en fonction du modele)
# qui contiendra le modele deja entraine

# remplacer MYMODELINSTANCE par le modele fitte sur les donnees