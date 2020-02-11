import numpy as np

import sklearn
import sklearn.decomposition

import sklearn.cluster
import sklearn.manifold

from . import tools

import joblib


def project_waveforms(method='pca_by_channel', catalogueconstructor=None, **params):
    """
    
    
    """


    #~ if waveforms.shape[0] == 0:
        #~ return None, None, None
    
    
    if method=='global_pca':
        projector = GlobalPCA(catalogueconstructor=catalogueconstructor, **params)
    elif method=='peak_max':
        projector = PeakMaxOnChannel(catalogueconstructor=catalogueconstructor, **params)
    elif method=='pca_by_channel':
        projector = PcaByChannel(catalogueconstructor=catalogueconstructor, **params)
    #~ elif method=='neighborhood_pca':
        #~ projector = NeighborhoodPca(waveforms, catalogueconstructor=catalogueconstructor, **params)
    else:
        raise NotImplementedError
    
    #~ features = projector.transform(waveforms2)
    features = projector.get_features(catalogueconstructor)
    channel_to_features = projector.channel_to_features
    return features, channel_to_features, projector


class GlobalPCA:
    def __init__(self, catalogueconstructor=None, n_components=5, **params):
        cc = catalogueconstructor
        
        self.n_components = n_components
        
        self.waveforms = cc.get_some_waveforms()
            
        flatten_waveforms = self.waveforms.reshape(self.waveforms.shape[0], -1)
        self.pca =  sklearn.decomposition.IncrementalPCA(n_components=n_components, **params)
        self.pca.fit(flatten_waveforms)
        
        
        #In GlobalPCA all feature represent all channels
        self.channel_to_features = np.ones((cc.nb_channel, self.n_components), dtype='bool')

    def get_features(self, catalogueconstructor):
        features = self.transform(self.waveforms)
        return features


    def transform(self, waveforms):
        flatten_waveforms = waveforms.reshape(waveforms.shape[0], -1)
        return self.pca.transform(flatten_waveforms)

class PeakMaxOnChannel:
    def __init__(self,  catalogueconstructor=None, **params):
        cc = catalogueconstructor
        
        #~ self.waveforms = waveforms
        # TODO something faster with only the max!!!!!
        self.waveforms = cc.get_some_waveforms()
        
        self.ind_peak = -catalogueconstructor.info['waveform_extractor_params']['n_left']
        #~ print('PeakMaxOnChannel self.ind_peak', self.ind_peak)
        
        
        #In full PeakMaxOnChannel one feature is one channel
        self.channel_to_features = np.eye(cc.nb_channel, dtype='bool')
    
    def get_features(self, catalogueconstructor):
        features = self.transform(self.waveforms)
        return features
    
        
    def transform(self, waveforms):
        #~ print('ici', waveforms.shape, self.ind_peak)
        features = waveforms[:, self.ind_peak, : ].copy()
        return features



#~ Parallel(n_jobs=n_jobs)(delayed(count_match_spikes)(sorting1.get_unit_spike_train(u1),
                                                                                  #~ s2_spiketrains, delta_frames) for
                                                      #~ i1, u1 in enumerate(unit1_ids))

#~ def get_pca_one_channel(wf_chan, chan, thresh, n_left, n_components_by_channel, params):
    #~ print(chan)
    #~ pca = sklearn.decomposition.IncrementalPCA(n_components=n_components_by_channel, **params)
    #~ wf_chan = waveforms[:,:,chan]
    #~ print(wf_chan.shape)
    #~ print(wf_chan[:, -n_left].shape)
    #~ keep = np.any((wf_chan>thresh) | (wf_chan<-thresh))
    #~ keep = (wf_chan[:, -n_left]>thresh) | (wf_chan[:, -n_left]<-thresh)

    #~ if keep.sum() >=n_components_by_channel:
        #~ pca.fit(wf_chan[keep, :])
        #~ return pca
    #~ else:
        #~ return None


class PcaByChannel:
    def __init__(self, catalogueconstructor=None, n_components_by_channel=3, **params):
        cc = catalogueconstructor
        
        thresh = cc.info['peak_detector_params']['relative_threshold']
        n_left = cc.info['waveform_extractor_params']['n_left']
        self.dtype = cc.info['internal_dtype']
        
        
        #~ self.waveforms = waveforms
        self.n_components_by_channel = n_components_by_channel
        
        some_peaks = cc.all_peaks[cc.some_peaks_index]
        self.pcas = []
        for chan in range(cc.nb_channel):
        #~ for chan in range(20):
            #~ print('fit', chan)
            sel = some_peaks['channel'] == chan
            wf_chan = cc.get_some_waveforms(peaks_index=cc.some_peaks_index[sel], channel_indexes=[chan])
            wf_chan = wf_chan[:, :, 0]
            #~ print(wf_chan.shape)
            
            if wf_chan.shape[0] > n_components_by_channel:
                pca = sklearn.decomposition.IncrementalPCA(n_components=n_components_by_channel, **params)
                pca.fit(wf_chan)
            else:
                pca = None
            self.pcas.append(pca)


            
            #~ pca = get_pca_one_channel(waveforms, chan, thresh, n_left, n_components_by_channel, params)
            
        #~ n_jobs = -1
        #~ self.pcas = joblib.Parallel(n_jobs=n_jobs)(joblib.delayed(get_pca_one_channel)(waveforms, chan, thresh, n_components_by_channel, params) for chan in range(cc.nb_channel))
        

        #In full PcaByChannel n_components_by_channel feature correspond to one channel
        self.channel_to_features = np.zeros((cc.nb_channel, cc.nb_channel*n_components_by_channel), dtype='bool')
        for c in range(cc.nb_channel):
            self.channel_to_features[c, c*n_components_by_channel:(c+1)*n_components_by_channel] = True

    def get_features(self, catalogueconstructor):
        cc = catalogueconstructor
        
        nb = cc.some_peaks_index.size
        n = self.n_components_by_channel
        
        features = np.zeros((nb, cc.nb_channel*self.n_components_by_channel), dtype=self.dtype)
        
        some_peaks = cc.all_peaks[cc.some_peaks_index]

        if cc.mode == 'sparse':
            channel_adjacency = cc.dataio.get_channel_adjacency(chan_grp=cc.chan_grp, adjacency_radius_um=cc.adjacency_radius_um)
            assert cc.info['peak_detector_params']['method'] == 'geometrical'
        
        for chan, pca in enumerate(self.pcas):
            if pca is None:
                continue
            #~ print('transform', chan)
            #~ sel = some_peaks['channel'] == chan
            
            if cc.mode == 'dense':
                wf_chan = cc.get_some_waveforms(peaks_index=cc.some_peaks_index, channel_indexes=[chan])
                wf_chan = wf_chan[:, :, 0]
                #~ print('dense', wf_chan.shape)
                features[:, chan*n:(chan+1)*n] = pca.transform(wf_chan)
            elif cc.mode == 'sparse':
                adj = channel_adjacency[chan]
                sel = np.in1d(some_peaks['channel'], channel_adjacency[chan])
                wf_chan = cc.get_some_waveforms(peaks_index=cc.some_peaks_index[sel], channel_indexes=[chan])
                wf_chan = wf_chan[:, :, 0]
                #~ print('sparse', wf_chan.shape)
                features[:, chan*n:(chan+1)*n][sel, :] = pca.transform(wf_chan)
            
            
        return features
        
    
    def transform(self, waveforms):
        n = self.n_components_by_channel
        all = np.zeros((waveforms.shape[0], waveforms.shape[2]*n), dtype=self.dtype)
        for c, pca in enumerate(self.pcas):
            if pca is None:
                continue
            #~ print(c)
            all[:, c*n:(c+1)*n] = pca.transform(waveforms[:, :, c])
        return all
    


#~ class NeighborhoodPca:
    #~ def __init__(self, waveforms, catalogueconstructor=None, n_components_by_neighborhood=6, radius_um=300., **params):
        #~ cc = catalogueconstructor
        
        #~ self.n_components_by_neighborhood = n_components_by_neighborhood
        #~ self.neighborhood = tools.get_neighborhood(cc.geometry, radius_um)
        
        #~ self.pcas = []
        #~ for c in range(cc.nb_channel):
            #~ neighbors = self.neighborhood[c, :]
            #~ pca = sklearn.decomposition.IncrementalPCA(n_components=n_components_by_neighborhood, **params)
            #~ wfs = waveforms[:,:,neighbors]
            #~ wfs = wfs.reshape(wfs.shape[0], -1)
            #~ pca.fit(wfs)
            #~ self.pcas.append(pca)

        #~ #In full NeighborhoodPca n_components_by_neighborhood feature correspond to one channel
        #~ self.channel_to_features = np.zeros((cc.nb_channel, cc.nb_channel*n_components_by_neighborhood), dtype='bool')
        #~ for c in range(cc.nb_channel):
            #~ self.channel_to_features[c, c*n_components_by_neighborhood:(c+1)*n_components_by_neighborhood] = True

    #~ def transform(self, waveforms):
        #~ n = self.n_components_by_neighborhood
        #~ all = np.zeros((waveforms.shape[0], waveforms.shape[2]*n), dtype=waveforms.dtype)
        #~ for c, pca in enumerate(self.pcas):
            #~ neighbors = self.neighborhood[c, :]
            #~ wfs = waveforms[:,:,neighbors]
            #~ wfs = wfs.reshape(wfs.shape[0], -1)
            #~ all[:, c*n:(c+1)*n] = pca.transform(wfs)
        #~ return all

