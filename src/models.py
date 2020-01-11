import numpy as np

import torch
import torch.nn as nn

from layers import ConvPoolReLU, ConvReLU, ConvBNReLUPool


class cnn(nn.Module):
    def __init__(self):
        super(cnn, self).__init__()

        self.features = nn.Sequential(
            ConvPoolReLU(1, 24, 3, 1, 1, (4, 2), (4, 2)),
            ConvPoolReLU(24, 48, 3, 1, 1, (4, 2), (4, 2)),
            ConvPoolReLU(48, 48, 3, 1, 1, (4, 2), (4, 2)),
            ConvReLU(48, 48, 3, 1, 1),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(1008, 10),
            #             nn.ReLU(inplace=True),
            #             nn.Dropout(0.5),
            #             nn.Linear(64, 10),
        )

    def forward(self, x):
        x = x.view(-1, 1, *x.shape[1:])

        x = self.features(x)
        x = self.classifier(x)

        return x


class cnn2(nn.Module):
    def __init__(self):
        super(cnn2, self).__init__()

        self.features = nn.Sequential(
            ConvPoolReLU(1, 24, 5, 1, 1, (4, 2), (4, 2)),
            ConvPoolReLU(24, 48, 5, 1, 1, (4, 2), (4, 2)),
            ConvReLU(48, 48, 5, 1, 1),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(1872, 64),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(64, 10)
        )

    def forward(self, x):
        x = x.view(-1, 1, *x.shape[1:])

        x = self.features(x)
        x = self.classifier(x)

        return x
    

class ScalableCnn1(nn.Module):
    """
    Compound Scaling based CNN
    see: https://arxiv.org/pdf/1905.11946.pdf
    """
    def __init__(self, compound_scales: tuple = (1, 1, 1)):
        super(ScalableCnn1, self).__init__()
        alpha, beta, gamma = compound_scales[0], compound_scales[1], compound_scales[2]
        
        initial_conv_inputs = [1, 32, 64, 64]
        initial_conv_outputs = [32, 64, 64, 64]
        initial_nb_conv = 4
        initial_dense_inputs = [1344]
        initial_dense_outputs = [10]
        initial_nb_dense = 1
        initial_resolution = (64, 173)
        
        # Apply compound scaling
        # depth ----
        scaled_nb_conv = np.floor(initial_nb_conv * alpha)
        scaled_nb_dense = np.floor(initial_nb_dense * alpha)
        
        if scaled_nb_conv != initial_nb_conv:  # Another conv layer must be created
            print("More conv layer must be created")
            gaps = np.array(initial_conv_outputs) - np.array(initial_conv_inputs) # average filter gap
            avg_gap = gaps.mean()
            
            while len(initial_conv_inputs) < scaled_nb_conv:
                initial_conv_outputs.append(int(np.floor(initial_conv_outputs[-1] + avg_gap)))
                initial_conv_inputs.append(initial_conv_outputs[-2])
                
            print("new conv layers:")
            print("inputs: ", initial_conv_inputs)
            print("ouputs: ", initial_conv_outputs)
            
        if scaled_nb_dense != initial_nb_dense:  # Another dense layer must be created
            print("More dense layer must be created")
            dense_list = np.linspace(initial_dense_inputs[0], initial_dense_outputs[-1], scaled_nb_dense+1)
            initial_dense_inputs = dense_list[:-1]
            initial_dense_outputs = dense_list[1:]
            
            print("new dense layers:")
            print("inputs: ", initial_dense_inputs)
            print("ouputs: ", initial_dense_outputs)
                
        # width ----
        scaled_conv_inputs = [int(np.floor(i * beta)) for i in initial_conv_inputs]
        scaled_conv_outputs = [int(np.floor(i * beta)) for i in initial_conv_outputs]
        scaled_dense_inputs = [int(np.floor(i * beta)) for i in initial_dense_inputs]
        scaled_dense_outputs = [int(np.floor(i * beta)) for i in initial_dense_outputs]
        
        # Check how many conv with pooling layer can be used
        nb_max_pooling = np.min([np.log2(initial_resolution[0]), int(np.log2(initial_resolution[1]))])
        nb_model_pooling = len(scaled_conv_inputs)
        
        if nb_model_pooling > nb_max_pooling:
            nb_model_pooling = nb_max_pooling
        
        # fixe initial and final conv & linear input
        scaled_conv_inputs[0] = 1
        scaled_dense_inputs[0] = self.calc_initial_dense_input(initial_resolution, nb_model_pooling, scaled_conv_outputs)
        scaled_dense_outputs[-1] = 10
        
        # ======== Create the convolution part ========
        features = []
        
        # Create the layers
        for idx, (inp, out) in enumerate(zip(scaled_conv_inputs, scaled_conv_outputs)):
            if idx < nb_model_pooling:
                dropout = 0.3 if idx != 0 else 0.0
                features.append(ConvBNReLUPool( inp, out, 3, 1, 1, (2, 2), (2, 2), dropout))
            
            else:
                features.append(ConvReLU(inp, out, 3, 1, 1))
            
        self.features = nn.Sequential(
            *features,
        )

        # ======== Craete the classifier part ========
        linears = []
        for inp, out in zip(scaled_dense_inputs[:-1], scaled_dense_outputs[:-1]):
            print(inp, out)
            linears.append(nn.Linear(inp, out))
            linears.append(nn.ReLU6(inplace=True))
            
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            *linears,
            nn.Linear(scaled_dense_inputs[-1], scaled_dense_outputs[-1])
        )
                      
    def forward(self, x):
        x = x.view(-1, 1, *x.shape[1:])

        x = self.features(x)
        x = self.classifier(x)
        
        return x
    
    def calc_initial_dense_input(self, initial_resolution, nb_model_pooling, conv_outputs):
        dim1 = initial_resolution[0]
        dim2 = initial_resolution[1]
        
        for i in range(int(nb_model_pooling)):
            dim1 = dim1 // 2
            dim2 = dim2 // 2
            
        return dim1 * dim2 * conv_outputs[-1]