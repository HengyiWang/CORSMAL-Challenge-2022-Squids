import numpy as np
import torch
import os
from torch.utils.data import Dataset
from tqdm.notebook import tqdm


class audioDataSet(Dataset):
  def __init__(self,root_pth,test=False,transform = None):
    print("Dataset initializing...")
    class_num=4
    self.audio_pth = os.path.join(root_pth, 'audios', 'mfcc')
    filling_type = np.load(os.path.join(root_pth, 'audios', 'filling_type.npy'))
    pouring_or_shaking = np.load(os.path.join(root_pth,  'audios', 'pouring_or_shaking.npy'))
    self.label = filling_type * pouring_or_shaking
    self.is_test=test
    self.each_class_size = []
    for i in range(class_num):
        self.each_class_size.append(np.count_nonzero(self.label==i))
    mx=0
    mn=1000
    for idx in tqdm(range(self.label.shape[0])):
        data=np.load(os.path.join(self.audio_pth, "{0:06d}".format(idx+1) + '.npy'), allow_pickle=True)
        tmp_max=np.max(data)
        tmp_min=np.min(data)
        if mx<tmp_max:
            mx=tmp_max
        if mn>tmp_min:
            mn=tmp_min
    self.mn=mn
    self.mx=mx
  def __len__(self):
    return self.label.shape[0]
  def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        lbl = -1

        if self.is_test is False:
            lbl = self.label[idx]
        data=np.load(os.path.join(self.audio_pth, "{0:06d}".format(idx+1) + '.npy'), allow_pickle=True)
        data= (data-self.mn)/(self.mx-self.mn)
        data=data.transpose(2,0,1)
        data=torch.from_numpy(data.astype(np.float32))
        return data , lbl
            
  def get_each_class_size(self):
    return np.array(self.each_class_size)



class Padding(object):
    def __init__(self, seq_len):
        self.seq_len = seq_len

    def __call__(self, sample, pred):
        #np.clip(pred, 0,1,out=pred)
        sample_len, input_dim = sample.shape
        #for i in range(sample_len):
        #    sample[i, :] *= pred[i]

        if sample_len >= self.seq_len:
            features = sample[:self.seq_len, :]
            return features
        else:
            start_seq = np.random.randint(0, self.seq_len - sample_len+1)
            #ini=[1]+[0]*(input_dim-1)
            ini=[0]*(input_dim)
            features = np.full((self.seq_len, input_dim),ini, dtype = float)
            features[start_seq:start_seq+sample_len, :] = sample
            return features

class MyLSTMDataset(torch.utils.data.Dataset):
    def __init__(self,root_pth,label, test=False,transform = None, padding_size = 100):
        class_num=3
        self.mid_pth = os.path.join(root_pth, 'T2_mid')
        self.pred_pth = os.path.join(root_pth, 'T2_pred')
        self.label = label  # gt['filling_level'].to_numpy()
        self.is_test=test
        self.each_class_size = []
        self.each_class_sum = [0]*class_num
        for i in range(class_num):
            self.each_class_size.append(np.count_nonzero(self.label==i))
        mx=0
        mn=1000
        len_mx = 0
        
        for idx in range(self.label.shape[0]):
            data=np.load(os.path.join(self.mid_pth, "{0:06d}".format(idx) + '.npy'), allow_pickle=True)
            self.each_class_sum[self.label[idx]]+=data.shape[0]
            if data.shape[0] > len_mx:
                len_mx=data.shape[0]
            tmp_max=np.max(data)
            tmp_min=np.min(data)
            if mx<tmp_max:
                mx=tmp_max
            if mn>tmp_min:
                mn=tmp_min
        self.mn=mn
        self.mx=mx
        self.pad = Padding(padding_size)
        print(len_mx)
            
    def __len__(self):
        return self.label.shape[0]
    
    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        lbl = -1

        if self.is_test is False:
            lbl = self.label[idx]
            
        data=np.load(os.path.join(self.mid_pth, "{0:06d}".format(idx) + '.npy'), allow_pickle=True)
        pred=np.load(os.path.join(self.pred_pth, "{0:06d}".format(idx) + '.npy'), allow_pickle=True)
        data = (data-self.mn)/(self.mx-self.mn)
        data = self.pad(data, pred)

        #np.clip(data, 0,1,out=data)
        data=torch.from_numpy(data.astype(np.float32))
        return data , lbl
            
    def get_each_class_size(self):
        return np.array(self.each_class_size)

    def get_each_class_avg_len(self):
        each_class_avg_len =  np.array(self.each_class_sum)/np.array(self.each_class_size)
        all_class_avg_len = np.sum(np.array(self.each_class_sum))/np.sum(np.array(self.each_class_size))
        return each_class_avg_len, all_class_avg_len