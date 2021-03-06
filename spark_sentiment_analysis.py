# -*- coding: utf-8 -*-
"""spark sentiment analysis.ipynb

Automatically generated by Colaboratory.

First, we use basic data science operations using pandas and numpy to explore the data. We import necessary libraries first.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

!pip install -U -q PyDrive

"""Since our dataset is in google drive, we need to connect collab to google drive to access the data. Uploading dataset to collab was slow. Also, such folders are deleted when new session is resumed."""

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials

# Authenticate and create the PyDrive client.
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)



downloaded = drive.CreateFile({'id':"1_IY06fo4FPwirTSbGWiGvAqoDeQjbqa0"}) 
downloaded.GetContentFile('training.csv')

"""So, we have extracted the training data files. Now using panda, we read the csv file and assign column names since there is no header in the dataset. """

cols = ['sentiment','id','date','query_string','user','text']

df = pd.read_csv("/content/training.csv",engine='python', header=None, names=cols)

df.head()

df.sentiment.value_counts()

"""We will be analysing the text of tweets so we drop the unrequired columns from the dataframe."""

df.drop(['id','date','query_string','user'],axis=1,inplace=True)

"""#Data preparation

First thing we need to do is to prepare the data. We observe the length and type of the text data and conclude following transformation operations to prepare them before analysis.
1. Removing HTML decoding in the text
2. Mentions removal
3. URL links removal
4. UTF marks removal
5. Hashtag removal
"""

df['pre_clean_len']=[len(t) for t in df.text]

from pprint import pprint
data_dict = {
    'sentiment':{
        'type':df.sentiment.dtype,
        'description':'sentiment class - 0:negative, 1:positive'
    },
    'text':{
        'type':df.text.dtype,
        'description':'tweet text'
    },
    'pre_clean_len':{
        'type':df.pre_clean_len.dtype,
        'description':'Length of the tweet before cleaning'
    },
    'dataset_shape':df.shape
}
pprint(data_dict)

#check the overall length of the strings with box plot
fig, ax = plt.subplots(figsize=(5, 5))
plt.boxplot(df.pre_clean_len)
plt.show()

#check the tweets that are more than 140 char long
df[df.pre_clean_len > 140].head(10)

!pip install beautifulsoup4

from bs4 import BeautifulSoup 
import re
from nltk.tokenize import WordPunctTokenizer
tok = WordPunctTokenizer()
pat1 = r'@[A-Za-z0-9]+'
pat2 = r'https?://[^ ]+'
www_pat = r'www.[^ ]+'
negations_dic = {"isn't":"is not", "aren't":"are not", "wasn't":"was not", "weren't":"were not",
                "haven't":"have not","hasn't":"has not","hadn't":"had not","won't":"will not",
                "wouldn't":"would not", "don't":"do not", "doesn't":"does not","didn't":"did not",
                "can't":"can not","couldn't":"could not","shouldn't":"should not","mightn't":"might not",
                "mustn't":"must not"}
neg_pattern = re.compile(r'\b(' + '|'.join(negations_dic.keys()) + r')\b')

combined_pat = r'|'.join((pat1, pat2))
def tweet_cleaner(text):
    soup = BeautifulSoup(text, 'lxml')
    souped = soup.get_text()
    stripped = re.sub(combined_pat, '', souped)
    try:
        clean = stripped.decode("utf-8-sig").replace(u"\ufffd", "?")
    except:
        clean = stripped
    clean = re.sub(www_pat, '', clean)
    letters_only = re.sub("[^a-zA-Z]", " ", clean)
    lower_case = letters_only.lower()
    neg_handled = neg_pattern.sub(lambda x: negations_dic[x.group()], lower_case)
    letters_only = re.sub("[^a-zA-Z]", " ", neg_handled)
    # During the letters_only process two lines above, it has created unnecessay white spaces,
    # I will tokenize and join together to remove unneccessary white spaces
    words = [x for x  in tok.tokenize(letters_only) if len(x) > 1]
    return (" ".join(words)).strip()
    
testing = df.text[:10]
test_result = []
for t in testing:
    test_result.append(tweet_cleaner(t))
test_result

nums=[0,1600000]
print ("Cleaning and parsing the tweets\n")
clean_tweet_texts=[]
for i in range(nums[0],nums[1]):
  if((i+1)%10000 == 0):
    print ("Tweets %d of %d has been processed" %(i+1, nums[1]))
  clean_tweet_texts.append(tweet_cleaner(df['text'][i]))

"""**Now, we save the cleaned data as CSV file which we will be using for the spark analysis.**"""

clean_df=pd.DataFrame(clean_tweet_texts, columns=['text'])
clean_df['target'] = df.sentiment
clean_df.head()

clean_df.count()

clean_df.to_csv('clean_tweet.csv',encoding='utf-8')
csv = 'clean_tweet.csv'
my_df = pd.read_csv(csv,index_col=0)
my_df.head()

"""#Now, we need to install findspark and pyspark on collab since they are not available by default.#"""

!apt-get install openjdk-8-jdk-headless -qq > /dev/null

!wget -q https://downloads.apache.org/spark/spark-3.0.0-preview2/spark-3.0.0-preview2-bin-hadoop2.7.tgz

!tar -xvf spark-3.0.0-preview2-bin-hadoop2.7.tgz

!pip install -q findspark

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = "/content/spark-3.0.0-preview2-bin-hadoop2.7"

import findspark
findspark.init()
import pyspark as ps
import warnings
from pyspark.sql import SQLContext

#we first create a SparkContext that operates in a cluster

try: 
  #create sparkcontext on CPUs available
  sc=ps.SparkContext.getOrCreate()
  sqlContext=SQLContext(sc)
  print("Just created a sparkcontet")
except ValueError: 
  warnings.warn("SparkContext already exists")

"""Spark has three different data structures available through its APIs: RDD, Dataframe, Dataset. We can use anyone based on the requirement. RDDs can offer low-level functionality and control but dataframe and dataset offers custom view and structure, offers high level operations, saves space and exectues at superior speeds."""

tweet_df=sqlContext.read.format('com.databricks.spark.csv').options(header='true', inferschema='true').load('/content/clean_tweet.csv')

type(tweet_df)

tweet_df.show(5)
tweet_df.count()

tweet_df=tweet_df.dropna()
tweet_df.count()

#breaking the datasets into training  and test sets
(train_set, test_set)=tweet_df.randomSplit([0.70, 0.30], seed=2000)

from pyspark.ml.feature import HashingTF, IDF, Tokenizer
from pyspark.ml.feature import StringIndexer
from pyspark.ml import Pipeline

tokenizer = Tokenizer(inputCol="text", outputCol="words")
hashtf = HashingTF(numFeatures=2**16, inputCol="words", outputCol='tf')
idf = IDF(inputCol='tf', outputCol="features", minDocFreq=5) #minDocFreq: remove sparse terms
label_stringIdx = StringIndexer(inputCol = "target", outputCol = "label")
pipeline = Pipeline(stages=[tokenizer, hashtf, idf, label_stringIdx])

pipelineFit = pipeline.fit(train_set)
train_df = pipelineFit.transform(train_set)
test_df = pipelineFit.transform(test_set)
train_df.show(5)

from pyspark.ml.classification import LogisticRegression
lr = LogisticRegression(maxIter=100)
lrModel = lr.fit(train_df)
predictions = lrModel.transform(test_df)
from pyspark.ml.evaluation import BinaryClassificationEvaluator
evaluator = BinaryClassificationEvaluator(rawPredictionCol="rawPrediction")
evaluator.evaluate(predictions)

type(predictions)

#can be written to a cluster like this
#predictions.write.csv("hdfs://cluster/usr/hdfs/prediction/result.csv")

"""BinaryClassificationEvaluator evaluates is by default areaUnderROC. Hence this is not the  measure of accuracy. So, we compute accuracy by counting the number of predictions matching the label and dividing it by the total entries."""

accuracy = predictions.filter(predictions.label == predictions.prediction).count() / float(test_set.count())
accuracy

"""Converting pyspark dataframe to pandas dataframe for visualization


"""

pandas_df = predictions.select("*").toPandas()

#plotting confusion matrix
from sklearn.metrics import classification_report, confusion_matrix
import itertools
def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)

    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

cnf_matrix=confusion_matrix(pandas_df["label"], pandas_df["prediction"], labels=[1,0])
print (cnf_matrix)

plt.figure()
plot_confusion_matrix(cnf_matrix, classes=['label=1','label=0'],normalize= False,  title='Confusion matrix')

pandas_df.hist(column="prediction")

pandas_df['clean_len']=[len(t) for t in pandas_df.text]
pandas_df.hist(column="clean_len")

