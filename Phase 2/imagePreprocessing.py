#imports
import numpy as np
import cv2
import os
from sklearn.cluster import KMeans
from scipy.spatial import distance
from sklearn.cluster import MiniBatchKMeans
from sklearn.svm import SVC
import sklearn.metrics as skmetrics
import random
import pickle
import imagePreprocessingUtils as ipu

#import glob

train_labels = []
test_labels = []


def preprocess_all_images():
    images_labels = []
    train_disc_by_class = {}
    test_disc_by_class = {}
    all_train_dis = []
    train_img_disc = []
    test_img_disc = []
    label_value = 0
    for (dirpath,dirnames,filenames) in os.walk(ipu.PATH):
        dirnames.sort()
        for label in dirnames:
            #print(label)
            if not (label == '.DS_Store'):
                for (subdirpath,subdirnames,images) in os.walk(ipu.PATH+'/'+label+'/'):
                    #print(len(images))
                    count = 0
                    train_features = []
                    test_features = []
                    for image in images: 
                        #print(label)
                        imagePath = ipu.PATH+'/'+label+'/'+image
                        #print(imagePath)
                        img = cv2.imread(imagePath)
                        if img is not None:
                            img = get_canny_edge(img)[0]
                            sift_disc = get_SIFT_descriptors(img)
                            print(sift_disc.shape)
                            if(count < (ipu.TOTAL_IMAGES * ipu.TRAIN_FACTOR * 0.01)):
                                print('Train:--------- Label is {} and Count is {}'.format(label, count)  )
                                #train_features.append(sift_disc)
                                train_img_disc.append(sift_disc)
                                all_train_dis.extend(sift_disc)
                                train_labels.append(label_value)
                            elif((count>=(ipu.TOTAL_IMAGES * ipu.TRAIN_FACTOR  * 0.01)) and count <ipu.TOTAL_IMAGES):
                                print('Test:--------- Label is {} and Count is {}'.format(label, count)  )
                                #test_features.append(sift_disc)
                                test_img_disc.append(sift_disc)
                                test_labels.append(label_value)
                            count += 1
                        #images_labels.append((label,sift_disc))
                #train_disc_by_class[label] = train_features
                #test_disc_by_class[label] = test_features
                label_value +=1
                    
    print('length of train features are %i' % len(train_img_disc))
    print('length of test features are %i' % len(test_img_disc))
    print('length of all train discriptors is {}'.format(len(all_train_dis)))
    #print('length of all train discriptors by class  is {}'.format(len(train_disc_by_class)))
    #print('length of all test disc is {}'.format(len(test_disc_by_class))) 
    return all_train_dis, train_img_disc, train_disc_by_class, test_disc_by_class, test_img_disc



def get_canny_edge(image):
   
    grayImage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Convert from RGB to HSV
    HSVImaage = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) 

    # Finding pixels with itensity of skin
    lowerBoundary = np.array([0,40,30],dtype="uint8")
    upperBoundary = np.array([43,255,254],dtype="uint8")
    skinMask = cv2.inRange(HSVImaage, lowerBoundary, upperBoundary)
    
    # blurring of gray scale using medianBlur
    skinMask = cv2.addWeighted(skinMask,0.5,skinMask,0.5,0.0)
    skinMask = cv2.medianBlur(skinMask, 5)
    skin = cv2.bitwise_and(grayImage, grayImage, mask = skinMask)
    #cv2.imshow("masked2",skin)
    
    #. canny edge detection
    canny = cv2.Canny(skin,60,60)
    #plt.imshow(img2, cmap = 'gray')
    return canny,skin

def get_SIFT_descriptors(canny):
    # Intialising SIFT
    surf = cv2.xfeatures2d.SURF_create()
    #surf.extended=True
    canny = cv2.resize(canny,(256,256))
    # computing SIFT descriptors
    kp, des = surf.detectAndCompute(canny,None)
    #print(len(des))
    #sift_features_image = cv2.drawKeypoints(canny,kp,None,(0,0,255),4)
    return des

### K-means is not used as data is large and requires a better computer with good specifications
def kmeans(k, descriptor_list):
    print('K-Means started.')
    print ('%i descriptors before clustering' % descriptor_list.shape[0])
    kmeanss = KMeans(k)
    kmeanss.fit(descriptor_list)
    visual_words = kmeanss.cluster_centers_ 
    return visual_words, kmeanss

def mini_kmeans(k, descriptor_list):
    print('Mini batch K-Means started.')
    print ('%i descriptors before clustering' % descriptor_list.shape[0])
    kmeans_model = MiniBatchKMeans(k)
    kmeans_model.fit(descriptor_list)
    print('Mini batch K means trained to get visual words.')
    filename = 'mini_kmeans_model.sav'
    pickle.dump(kmeans_model, open(filename, 'wb'))
    return kmeans_model


def get_histograms(discriptors_by_class,visual_words, cluster_model):
    histograms_by_class = {}
    total_histograms = []
    for label,images_discriptors in discriptors_by_class.items():
        print('Label: %s' % label)
        histograms = []
        #    loop for all images 
        for each_image_discriptors in images_discriptors:
            
            ## manual method to calculate words occurence as histograms
            '''histogram = np.zeros(len(visual_words))
            # loop for all discriptors in a image discriptorss 
            for each_discriptor in each_image_discriptors:
                #list_words = visual_words.tolist()
                a = np.array([visual_words])
                index = find_index(each_discriptor, visual_words)
                #print(index)
                #del list_words
                histogram[index] += 1
            print(histogram)'''
            
            ## using cluster model
            raw_words = cluster_model.predict(each_image_discriptors)
            hist =  np.bincount(raw_words, minlength=len(visual_words))
            print(hist)
            histograms.append(hist)
        histograms_by_class[label] = histograms
        total_histograms.append(histograms)
    print('Histograms succesfully created for %i classes.' % len(histograms_by_class))
    return histograms_by_class, total_histograms
    
def dataSplit(dataDictionary):
    X = []
    Y = []
    for key,values in dataDictionary.items():
        for value in values:
            X.append(value)
            Y.append(key)
    return X,Y
        
def predict_svm(X_train, X_test, y_train, y_test):
    svc=SVC(kernel='linear') 
    print("Support Vector Machine started.")
    svc.fit(X_train,y_train)
    filename = 'svm_model.sav'
    pickle.dump(svc, open(filename, 'wb'))
    y_pred=svc.predict(X_test)
    np.savetxt('submission_svm.csv', np.c_[range(1,len(y_test)+1),y_pred,y_test], delimiter=',', header = 'ImageId,PredictedLabel,TrueLabel', comments = '', fmt='%d')
    calculate_metrics("SVM",y_test,y_pred)
    

def calculate_metrics(method,label_test,label_pred):
    print("Accuracy score for ",method,skmetrics.accuracy_score(label_test,label_pred))
    print("Precision_score for ",method,skmetrics.precision_score(label_test,label_pred,average='micro'))
    print("f1 score for ",method,skmetrics.f1_score(label_test,label_pred,average='micro'))
    print("Recall score for ",method,skmetrics.recall_score(label_test,label_pred,average='micro'))


### STEP:1 SIFT discriptors for all train and test images with class seperation

all_train_dis,train_img_disc, train_disc_by_class, test_disc_by_class, test_img_disc  = preprocess_all_images()

##  deleting these variables as they are not used with mini batch k means
del train_disc_by_class, test_disc_by_class 

### STEP:2 MINI K-MEANS 

mini_kmeans_model = mini_kmeans(ipu.N_CLASSES * ipu.CLUSTER_FACTOR, np.array(all_train_dis))

del all_train_dis

### Collecting VISUAL WORDS for all images (train , test)

print('Collecting visual words for train .....')
train_images_visual_words = [mini_kmeans_model.predict(visual_words) for visual_words in train_img_disc]
print('Visual words for train data collected. length is %i' % len(train_images_visual_words))

print('Collecting visual words for test .....')
test_images_visual_words = [mini_kmeans_model.predict(visual_words) for visual_words in test_img_disc]
print('Visual words for test data collected. length is %i' % len(test_images_visual_words))


### STEP:3 HISTOGRAMS (findiing the occurence of each visual word of images in total words)
## Can be calculated using get_histograms function also manually

print('Calculating Histograms for train...')
bovw_train_histograms = np.array([np.bincount(visual_words, minlength=ipu.N_CLASSES * ipu.CLUSTER_FACTOR) for visual_words in train_images_visual_words])
print('Train histograms are collected. Length : %i ' % len(bovw_train_histograms))

print('Calculating Histograms for test...')
bovw_test_histograms = np.array([np.bincount(visual_words, minlength=ipu.N_CLASSES * ipu.CLUSTER_FACTOR) for visual_words in test_images_visual_words])
print('Test histograms are collected. Length : %i ' % len(bovw_test_histograms))

print('Each histogram length is : %i' % len(bovw_train_histograms[0]))
#----------------------
print('============================================')

# preperaing for training svm
X_train = bovw_train_histograms
X_test = bovw_test_histograms
Y_train = train_labels
Y_test = test_labels

#print(Y_train)
### shuffling 

buffer  = list(zip(X_train, Y_train))
random.shuffle(buffer)
random.shuffle(buffer)
random.shuffle(buffer)
X_train, Y_train = zip(*buffer)
#print(Y_train)

buffer  = list(zip(X_test, Y_test))
random.shuffle(buffer)
random.shuffle(buffer)
X_test, Y_test = zip(*buffer)

print('Length of X-train:  %i ' % len(X_train))
print('Length of Y-train:  %i ' % len(Y_train))
print('Length of X-test:  %i ' % len(X_test))
print('Length of Y-test:  %i ' % len(Y_test))

predict_svm(X_train, X_test,Y_train, Y_test)


#######################################################
'''


#STEP:2 K-MEANS clustering to get visual words 

visual_words, cluster_model = kmeans(ipu.N_CLASSES * 8, np.array(all_train_dis))

print(' Length of Visual words using k-means= %i' % len(visual_words))
print(type(visual_words))
print(visual_words.shape)


print('Histograms creation started for training set.')
   
bovw_train_histograms_by_class = get_histograms(train_disc_by_class,visual_words, cluster_model)[0]
print('Histograms created with k-means.')


for key, values in bovw_train_histograms_by_class.items():
    for value in values:
        print(value)
   

print('Histograms creation started for testing set.')
bovw_test_histograms_by_class = get_histograms(test_disc_by_class,visual_words, cluster_model)[0]
print('Histograms created.')

X_train, Y_train = dataSplit(bovw_train_histograms_by_class)

print('Length of x_train are % i ' % len(X_train))
print('Length of y_train are % i ' % len(Y_train))

X_test, Y_test = dataSplit(bovw_test_histograms_by_class)

print('Length of x_test are % i ' % len(X_test))
print('Length of y_test are % i ' % len(Y_test))


X_train, Y_train = dataSplit(bovw_train_histograms_by_class)
predict_svm(X_train, X_test,Y_train, Y_test)

'''