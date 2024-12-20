

# -*- coding: utf-8 -*-
"""
Copyright   I3S CNRS UCA

This code implement the cross validation Train Validate Test

https://scikit-learn.org/stable/modules/cross_validation.html

When using this code , please cite: 
    
Nolwenn Peyratout, Johan Lassen, Sonia Dagnino, Palle Villesen and Michel Barlaud. 
Predicting biological age with metabolomic data using a fully connected neural
network (FCNN) and feature selection with a sparse bilevel l1inf projection.


 Michel Barlaud, Guillaume Perez, and Jean-Paul Marmorat.
Linear time bi-level l1,infini projection ; application to feature selection and
sparsification of auto-encoders neural networks.
http://arxiv.org/abs/2407.16293, 2024.        
"""
#%%
import os

import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
import torch
from torch import nn
from sklearn import metrics
from scipy.stats import wasserstein_distance

import functions.functions_torch_regression_V4 as ft
import functions.functions_network_pytorch as fnp


#%%

if __name__ == "__main__":

    ######## Parameters ########
    start_time= time.time()
    # Set seed
    SEEDS = [5]

    # Set device (GPU or CPU)
    DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    nfolds = 4  # Number of folds for the cross-validation process
    N_EPOCHS = 30  # Number of epochs for the first descent
    N_EPOCHS_MASKGRAD = 40  # Number of epochs for training masked gradient
    LR = 0.0005  # Learning rate
    BATCH_SIZE = 50  # Optimize the trade off between accuracy and computational time

    # unit scaling of the input data
    doScale = False
    # log transform of the input data
    doLog = False
    #row normalization of the input data
    doRowNorm = False
    doMeanto1 = False
    
    #distribution normalisation for Wasserstein
    WDNorm = False

    # Regression
    # Loss function
    criterion_regression = nn.MSELoss(reduction="sum")
    #criterion_regression = nn.SmoothL1Loss(reduction="sum")  # SmoothL1Loss

    
    ## Dataset choice
    file_name = 'Synth_Reg_500f_64inf_500s.csv'
    file_name_test = 'Synth_Reg_500f_64inf_150s.csv'

    ## Choose Architecture
    #net_name = 'LeNet'
    #net_name = "netBio"
    net_name = 'FAIR' 
    #net_name = 'dnn'
    
    #Choose if normalisation layer in the network 
    norm = False 
    
    #Choose nb of hidden neurons for NetBio and Fair network 
    n_hidden = 300 # amount of neurons on netbio's hidden layer

    
    run_model = "No_proj"  # default model run
    # Do projection at the middle layer or not
    DO_PROJ_MIDDLE = False

    ETA = 1 # Controls feature selection (projection) (L1, L11, L21)
    GRADIENT_MASK = True # Whether to do a second descent

    ## Choose projection function
    if not GRADIENT_MASK:
        TYPE_PROJ = "No_proj"
        TYPE_PROJ_NAME = "No_proj"
    else:

        #TYPE_PROJ = ft.proj_l1ball  # projection l1
        #TYPE_PROJ = ft.proj_l11ball  # original projection l11 (col-wise zeros)
        #TYPE_PROJ = ft.proj_l21ball   # projection l21
        #TYPE_PROJ = ft.proj_l1infball  # projection l1,inf
        TYPE_PROJ = ft.bilevel_proj_l1Inftyball  # projection bilevel l1,inf

        TYPE_PROJ_NAME = TYPE_PROJ.__name__
        
    #TYPE_ACTIVATION = "tanh"
    #TYPE_ACTIVATION = "gelu"
    #TYPE_ACTIVATION = "relu"
    TYPE_ACTIVATION = "silu"

    AXIS = 1  #  1 for columns (features), 0 for rows (neurons)
    TOL = 1e-3  # error margin for the L1inf algorithm and gradient masking

    DoTopGenes = True  # Compute feature rankings
    
    DoSparsity= True # Show the sparsity of the SAE

    # Save Results or not
    SAVE_FILE = True

    ######## Main routine ########
    
    # Output Path
    outputPath = (
        "results_stat"
        + "/"
        + file_name.split(".")[0]
        + "/"
    )
    plotPath = (
        "plots"
        + "/"
        + file_name.split(".")[0]
        + "/"
    )
    if not os.path.exists(outputPath):  # make the directory if it does not exist
        os.makedirs(outputPath)
        
    if not os.path.exists(plotPath):  # make the directory if it does not exist
        os.makedirs(plotPath)

    # Load data
    X, Y,  feature_names, label_name_train,  patient_name, gaussianKDE , divided = ft.ReadData(
        file_name, doScale=doScale, doLog=doLog,  doRowNorm = doRowNorm, doMeanto1 = doMeanto1
    )
    
    X_test, y_test,  feature_names_test, label_name_test,  patient_name_test, gaussianKDETest , divided = ft.ReadData(
        file_name_test, doScale=doScale, doLog=doLog,  doRowNorm = doRowNorm, doMeanto1 = doMeanto1
    )

    feature_len = len(feature_names)
    print(f"Number of features: {feature_len}")
    seed_idx = 0
    data_train = np.zeros((nfolds * len(SEEDS), 6))
    data_test = np.zeros((nfolds * len(SEEDS), 6))
    
    data_finalTest = np.zeros((nfolds * len(SEEDS), 6))
    
    sparsity_matrix= np.zeros((nfolds * len(SEEDS), 1))
    sparsity_matrix_retraing= np.zeros((nfolds * len(SEEDS), 1))
    
    
    
    for seed in SEEDS:
        
        
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        for fold_idx in range(nfolds):
            start_time = time.time()
            train_dl, test_dl, train_len, test_len, Ytest = ft.CrossVal(
                X, Y, patient_name, BATCH_SIZE, fold_idx, seed
            )
            print(
                "Len of train set: {}, Len of test set: {}".format(train_len, test_len)
            )
            print("----------- Start fold ", fold_idx, "----------------")
            
            print("----------- Start Training ---------------")
            # Define the SEED to fix the initial parameters
            
            
            data_encoder, net = ft.training(seed, feature_len, TYPE_ACTIVATION,
                        DEVICE, n_hidden, norm, feature_names,GRADIENT_MASK,
                        net_name, LR, criterion_regression, train_dl,
                        train_len, gaussianKDE, test_dl, test_len, outputPath,
                        TYPE_PROJ,SEEDS,fold_idx,nfolds, N_EPOCHS,
                        N_EPOCHS_MASKGRAD, DO_PROJ_MIDDLE, ETA, AXIS, TOL)
            end_time = time.time()

            # Calculate and print the execution time
            execution_time = end_time - start_time
            print(f"Execution time for training : {execution_time} seconds for fold {fold_idx}")
            
            data_encoder = data_encoder.cpu().detach().numpy()

            (
                data_encoder_test,
                Ytrue,
                Ypred,
            ) = ft.runBestNet(
                test_dl,
                outputPath,
                fold_idx,
                net,
                feature_names,
                test_len,
                ETA
            )
           

            if seed == SEEDS[-1]:
                if fold_idx == 0:
                    Ytruef = Ytrue
                    Ypredf = Ypred
                    LP_test = data_encoder_test.detach().cpu().numpy()
                else:
                    Ytruef = np.concatenate((Ytruef, Ytrue))
                    Ypredf = np.concatenate((Ypredf, Ypred))
                    LP_test = np.concatenate(
                        (LP_test, data_encoder_test.detach().cpu().numpy())
                    )
                plt.figure()
                
                sns.kdeplot(data=list(np.array(Ypredf) * int(divided)), fill=True,
                            bw_adjust=0.4, color="tab:blue")
                sns.kdeplot(data=list(np.array(Ytruef) * int(divided)), fill=True,
                            bw_adjust=0.4, color="tab:green")
                plt.xlabel('Age')
                plt.ylabel('Density')
                plt.title('Age Distribution between predicted and the truth for best net')
                plt.legend(["Predicted","Truth"])
                plt.savefig('plots/distribution'+str(seed)+'.png')
                plt.show()
                
                
            label_predicted = data_encoder[:, 0]
            labels_encoder = data_encoder[:, -1]
            data_encoder_test = data_encoder_test.cpu().detach().numpy()
            # mse score
            data_train[seed_idx * 4 + fold_idx, 0] = metrics.mean_squared_error(
                label_predicted, labels_encoder
            )
            

            label_predicted_test = data_encoder_test[:, 0]
            labels_encodertest = data_encoder_test[:, -1]
            data_test[seed_idx * 4 + fold_idx, 0] = metrics.mean_squared_error(
                label_predicted_test, labels_encodertest
            )
            
            data_train[seed_idx * 4 + fold_idx, 1] = metrics.mean_squared_error(
                label_predicted, labels_encoder
            )**0.5 * divided
            

            data_test[seed_idx * 4 + fold_idx, 1] = metrics.mean_squared_error(
                label_predicted_test, labels_encodertest
            )**0.5 * divided
            
            #MAE score
            data_train[seed_idx * 4 + fold_idx, 2] = metrics.mean_absolute_error(
                label_predicted, labels_encoder
            )* divided
            
            data_test[seed_idx * 4 + fold_idx, 2] = metrics.mean_absolute_error(
                label_predicted_test, labels_encodertest
            )* divided
            
            data_train[seed_idx * 4 + fold_idx, 3], data_train[seed_idx * 4 + fold_idx, 4] = ft.valueGap(
                label_predicted, labels_encoder, divided
            )
            

            data_test[seed_idx * 4 + fold_idx, 3], data_test[seed_idx * 4 + fold_idx, 4] = ft.valueGap(
                 label_predicted_test, labels_encodertest, divided
             )
             
            if WDNorm:
                #WasserteinDistance
                data_train[seed_idx * 4 + fold_idx, 5] = wasserstein_distance(
                    labels_encoder/ np.sum(labels_encoder),label_predicted/ np.sum(label_predicted))* divided
                
                
                data_test[seed_idx * 4 + fold_idx, 5] =  wasserstein_distance(
                    labels_encodertest/ np.sum(labels_encodertest),label_predicted_test/ np.sum(label_predicted_test))* divided
            else: 
                data_train[seed_idx * 4 + fold_idx, 5] = wasserstein_distance(
                    labels_encoder,label_predicted)* divided
                
                
                data_test[seed_idx * 4 + fold_idx, 5] =  wasserstein_distance(
                    labels_encodertest,label_predicted_test)* divided
                
            
            
            # Get Top Genes of each class

            # method = 'Shap'   # (SHapley Additive exPlanation) needs a nb_samples
            nb_samples = 300  # Randomly choose nb_samples to calculate their Shap Value, time vs nb_samples seems exponential
            # method = 'Captum_ig'   # Integrated Gradients
            method = "Captum_dl"  # Deeplift
            # method = 'Captum_gs'  # GradientShap

            tps1 = time.perf_counter()
            print("Running topGenes...")
            df_topGenes = ft.topGenes(
                X,
                Y,
                feature_names,
                feature_len,
                method,
                nb_samples,
                DEVICE,
                net,
                TOL
            )
            df_topGenes.index = df_topGenes.iloc[:, 0]
            print("topGenes finished")
            tps2 = time.perf_counter()
            
            if fold_idx != 0:  #not first fold need to get previous topGenes
                df = pd.read_csv(
                    "{}{}_topGenes_{}_{}.csv".format(
                        outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
                    ),
                    sep=";",
                    header=0,
                    index_col=0,
                )
                df_topGenes.index = df_topGenes.iloc[:, 0]
                df_topGenes = df.join(df_topGenes.iloc[:, 1], lsuffix="_",)

            df_topGenes.to_csv(
                "{}{}_topGenes_{}_{}.csv".format(
                    outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
                ),
                sep=";",
            )
            tps2 = time.perf_counter()
            print("Execution time topGenes  : ", tps2 - tps1)
                
            if DoSparsity: 
                mat_in = net.state_dict()["encoder.0.weight"]
                mat_col_sparsity = ft.sparsity_col(mat_in, device=DEVICE)
                sparsity_matrix[seed_idx * 4+ fold_idx, 0] = mat_col_sparsity
            
            weights, spasity_w = fnp.weights_and_sparsity(net, TOL)
            spasity_percentage_entry = {}
            for keys in weights.keys():
                spasity_percentage_entry[keys] = spasity_w[keys] * 100
            print("sparsity % of all layers entry \n", spasity_percentage_entry)
            layer_list = [x for x in weights.values()]
            ft.show_img(layer_list, file_name)
            
            print("---------------- Start Testing on the 20% ----------------")
            
            #load les dl
            dtest = ft.LoadDataset(X_test, y_test, list(range(len(X_test))))
            # _, test_set = torch.utils.data.random_split(dtest, [0])
            test_dl = torch.utils.data.DataLoader(dtest, batch_size=1)
            
            print(
                "Len of test set: {}".format(len(dtest))
            )
            
            (
                data_encoder_test20,
                Ytrue20,
                Ypred20,
            ) = ft.runBestNet(
                test_dl,
                outputPath,
                fold_idx,
                net,
                feature_names,
                test_len,
                ETA
            )
            
            
            if fold_idx == 0:
                Ytruef20 = Ytrue20
                Ypredf20 = Ypred20
                LP_test20 = data_encoder_test20.detach().cpu().numpy()
            else:
                Ytruef20 = np.concatenate((Ytruef20, Ytrue20))
                Ypredf20 = np.concatenate((Ypredf20, Ypred20))
                LP_test20 = np.concatenate(
                    (LP_test20, data_encoder_test20.detach().cpu().numpy())
                )
            plt.figure()
            sns.kdeplot(data=list(np.array(Ypredf20) * int(divided)), fill=True,
                        bw_adjust=0.4, color="tab:blue")
            sns.kdeplot(data=list(np.array(Ytruef20) * int(divided)), fill=True,
                        bw_adjust=0.4, color="tab:green")
            plt.xlabel('Age')
            plt.ylabel('Density')
            plt.title('Age Distribution between predicted and the truth for the test set')
            plt.legend(["Predicted","Truth"])
            plt.savefig('plots/distribution-test-'+str(seed)+'-'+str(fold_idx)+'.png')
            plt.show()
            
            ft.figPerAge(np.array(Ytruef20), np.array(Ypredf20),seed, fold_idx)
                
            data_encoder_test20 = data_encoder_test20.cpu().detach().numpy()
            # mse score
            
            label_predicted_test20 = data_encoder_test20[:, 0]
            labels_encodertest20 = data_encoder_test20[:, -1]
            data_finalTest[seed_idx * 4 + fold_idx, 0] = metrics.mean_squared_error(
                label_predicted_test20, labels_encodertest20
            )
        
            data_finalTest[seed_idx * 4 + fold_idx, 1] = metrics.mean_squared_error(
                label_predicted_test20, labels_encodertest20
            )**0.5 * divided
            
            #MAE score
            data_finalTest[seed_idx * 4 + fold_idx, 2] = metrics.mean_absolute_error(
                label_predicted_test20, labels_encodertest20
            )* divided
            

            data_finalTest[seed_idx * 4 + fold_idx, 3], data_finalTest[seed_idx * 4 + fold_idx, 4]= ft.valueGap(
                 label_predicted_test20, labels_encodertest20, divided
             )
             
            if WDNorm:
                #WasserteinDistance
                data_train[seed_idx * 4 + fold_idx, 5] = wasserstein_distance(
                    labels_encodertest20/ np.sum(labels_encodertest20),
                    label_predicted_test20/ np.sum(label_predicted_test20))* divided
                
            else: 
                data_finalTest[seed_idx * 4 + fold_idx, 5] = wasserstein_distance(
                labels_encodertest20, label_predicted_test20,
            )* divided
            


        # Moyenne sur les SEED
        if DoTopGenes:
            df = pd.read_csv(
                "{}{}_topGenes_{}_{}.csv".format(
                    outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
                ),
                sep=";",
                header=0,
                index_col=0,
            )
            df_val = df.values[1:, 1:].astype(float)
            df_mean = df_val.mean(axis=1).reshape(-1, 1)
            df_std = df_val.std(axis=1).reshape(-1, 1)
            df = pd.DataFrame(
                np.concatenate((df.values[1:, :], df_mean, df_std), axis=1),
                columns=[
                    "Features",
                    "Fold 1",
                    "Fold 2",
                    "Fold 3",
                    "Fold 4",
                    "Mean",
                    "Std",
                ],
            )
            df_topGenes = df
            df_topGenes = df_topGenes.sort_values(by="Mean", ascending=False)
            df_topGenes = df_topGenes.reindex(
                columns=[
                    "Features",
                    "Mean",
                    "Fold 1",
                    "Fold 2",
                    "Fold 3",
                    "Fold 4",
                    "Std",
                ]
            )
            df_topGenes.to_csv(
                "{}{}_topGenes_{}_{}.csv".format(
                    outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
                ),
                sep=";",
                index=0,
            )

            if seed == SEEDS[0]:
                df_topGenes_mean = df_topGenes.iloc[:, 0:2]
                df_topGenes_mean.index = df_topGenes.iloc[:, 0]
            else:
                df = pd.read_csv(
                    "{}{}_topGenes_Mean_{}_{}.csv".format(
                        outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
                    ),
                    sep=";",
                    header=0,
                    index_col=0,
                )
                df_topGenes.index = df_topGenes.iloc[:, 0]
                df_topGenes_mean = df.join(df_topGenes.iloc[:, 1], lsuffix=seed)

            df_topGenes_mean.to_csv(
                "{}{}_topGenes_Mean_{}_{}.csv".format(
                    outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
                ),
                sep=";",
            )
            
            if DoSparsity: 
                mat_in = net.state_dict()["encoder.0.weight"]
                mat_col_sparsity = ft.sparsity_col(mat_in, device=DEVICE)
                sparsity_matrix_retraing[seed_idx * 4+ fold_idx, 0] = mat_col_sparsity
        
        labelspred = pd.read_csv(
           "{}Labelspred_value{}.csv".format(outputPath, ETA), sep=";", header=0
           ) 
        
        plt.figure()
        
        sns.kdeplot(data=list(np.array(labelspred['Predicted Value']) * int(divided)),
                    fill=True, bw_adjust=0.4, color="tab:blue")
        sns.kdeplot(data=list(np.array(labelspred['Initial Value']) * int(divided)),
                    fill=True, bw_adjust=0.4, color="tab:green")
        plt.xlabel('Age')
        plt.ylabel('Density')
        plt.title('Age Distribution between predicted and the truth')
        plt.legend(["Predicted","Truth"])
        plt.savefig('plots/distribution'+str(seed)+str(ETA)+'.png')
        plt.show()
        
        
        seed_idx += 1

    # metrics
    df_metricsTrain, df_metricsTest = ft.packMetricsResult(
        data_train, data_test, nfolds * len(SEEDS)
    )

    
    reg_metrics = ["MSE","RMSE", "MAE","Negative gap", "Positive gap", "WD"]
    df_metricsTrain_classif = df_metricsTrain[reg_metrics]
    df_metricsTest_classif = df_metricsTest[reg_metrics]
    print("\nMetrics Train")
    print(df_metricsTrain_classif)
    print("\nMetrics Validation")
    print(df_metricsTest_classif)
    
    df_metricsFinalTest = ft.packMetric(data_finalTest, nfolds*len(SEEDS))
    df_metrics_FinalTest = df_metricsFinalTest[reg_metrics]
    print("\nMetrics Final Test")
    print(df_metrics_FinalTest)
    

    if DoSparsity:
        #make df for the sparsity:
        columns = (
                ["Sparsity"]
            )
        ind_df = ["Fold " + str(x + 1) for x in range(nfolds* len(SEEDS))]
    
        df_sparcity = pd.DataFrame(sparsity_matrix, index=ind_df, columns=columns)
        df_sparcity.loc["Mean"] = df_sparcity.apply(lambda x: x.mean())
        df_sparcity.loc["Std"] = df_sparcity.apply(lambda x: x.std())
        print('\n Sparsity on the encoder for the training')
        print(df_sparcity)
        print(f'\n On average we have {round(100-df_sparcity.loc["Mean", "Sparsity"])}% features selected, thus {round(((100- df_sparcity.loc["Mean", "Sparsity"])/100)*feature_len)} features')
    

    if DoTopGenes:
        df = pd.read_csv(
            "{}{}_topGenes_Mean_{}_{}.csv".format(
                outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
            ),
            sep=";",
            header=0,
            index_col=0,
        )
        df_val = df.values[:, 1:].astype(float)
        df_mean = df_val.mean(axis=1).reshape(-1, 1)
        df_std = df_val.std(axis=1).reshape(-1, 1)
        df_meanstd = df_std / df_mean
        col_seed = ["Seed " + str(i) for i in SEEDS]
        df = pd.DataFrame(
            np.concatenate((df.values[:, :], df_mean, df_std, df_meanstd), axis=1),
            columns=["Features"] + col_seed + ["Mean", "Std", "Mstd"],
        )
        df_topGenes = df
        df_topGenes = df_topGenes.sort_values(by="Mean", ascending=False)
        df_topGenes = df_topGenes.reindex(
            columns=["Features", "Mean"] + col_seed + ["Std", "Mstd"]
        )
        df_topGenes.to_csv(
            "{}{}_topGenes_Mean_{}_{}.csv".format(
                outputPath, str(TYPE_PROJ_NAME), method, str(nb_samples)
            ),
            sep=";",
            index=0,
        )

    weights_entry, spasity_w_entry = fnp.weights_and_sparsity(net, TOL)
    weights, spasity_w = fnp.weights_and_sparsity(net, TOL)
    
    layer_list = [x for x in weights.values()]
    titile_list = [x for x in spasity_w.keys()]

    ft.show_img(layer_list, file_name)

    # Loss figure
    if os.path.exists(file_name.split(".")[0] + "_Loss_No_proj.npy") and os.path.exists(
        file_name.split(".")[0] + "_Loss_MaskGrad.npy"
    ):
        loss_no_proj = np.load(file_name.split(".")[0] + "_Loss_No_proj.npy")
        loss_with_proj = np.load(file_name.split(".")[0] + "_Loss_MaskGrad.npy")
        plt.figure()
        plt.title(file_name.split(".")[0] + " Loss")
        plt.xlabel("Epoch")
        plt.ylabel("TotalLoss")
        plt.plot(loss_no_proj, label="No projection")
        plt.plot(loss_with_proj, label="With projection ")
        plt.legend()
        plt.show()
        
    if SAVE_FILE:
        df_metricsFinalTest.to_csv(
            "{}{}_acctest.csv".format(outputPath, str(TYPE_PROJ_NAME)), sep=";"
        )
        if DoSparsity:
            df_sparcity.to_csv(
                "{}{}_sparsity.csv".format(outputPath, str(TYPE_PROJ_NAME)), sep=";"
                )
   
    end_time= time.time()
    execution_time=end_time-start_time
    print(f"Execution time: {execution_time} seconds")
    
    

