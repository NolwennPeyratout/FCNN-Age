# FCNN-Age
This is the code from: Predicting biological age with metabolomic data using a fully connected neural network (FCNN) and feature selection with a sparse bilevel l1inf projection. 

In this repository, you will find the code used in the statistical study described in the paper.

When using this code please cite the following: 

> Michel Barlaud, Guillaume Perez, and Jean-Paul Marmorat.
Linear time bi-level l1,infini projection ; application to feature selection and
sparsification of auto-encoders neural networks.
http://arxiv.org/abs/2407.16293, 2024

# Table of Contents
1. [Repository Content](#Repository-content)
2. [Installation](#Installation)
3. [How to use](#How-to-use)


### **Repository Contents**
|File/Folder | Description |
|:---|:---:|
|`script_FCNN_Regression_TVT.py`|Main script to train and evaluate the neural network|
|`datas`|Where the data should be, not given via GitHub|
|`functions`|Contains dedicated functions for the main script|
    
### **Installation** 
---

To run this code, you will need :
- A version of Python 3.8 or newer. If you are new to using Python, we recommend downloading Anaconda ([here](https://www.anaconda.com/products/individual)) and running the code with Spyder (available by default from the Anaconda navigator).
- [Pytorch](https://pytorch.org/get-started/locally/).
- The following packages, all of which except Captum and SHAP are **usually included in the anaconda distribution** : [numpy](https://numpy.org/install/), [matplotlib](https://matplotlib.org/stable/users/installing/index.html), [scikit-learn](https://scikit-learn.org/stable/install.html), [pandas](https://pandas.pydata.org/getting_started.html), [shap](https://pypi.org/project/shap/), [captum](https://captum.ai/#quickstart). You can install anaconda navigator's built-in environment manager to install any package.

See `requirements.txt` for the exact versions on which this code was developed.

### **How to use**

Everything is ready, you can just run the script you want using, for example, the run code button of your Spyder IDE. Alternatively, you can run the command `python [script_name].py` in the Anaconda Prompt from the root of this folder (i.e. where you downloaded and unzipped this repository).

Each script will produce results (statistical metrics, top features...) in a results folder.

You can change other parameters near each script's start.
