import tensorflow as tf

import numpy as np

from scipy.integrate import odeint

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import seaborn as sns

from plotting import newfig, savefig

import time

import uuid

#@tf.RegisterGradient("HeavisideGrad")
#def _heaviside_grad(unused_op: tf.Operation, grad: tf.Tensor):
#    return tf.maximum(0.0, 1.0 - tf.abs(unused_op.inputs[0])) * grad


def heaviside(x: tf.Tensor, g: tf.Graph = tf.get_default_graph()):
    custom_grads = {
        "Identity": "HeavisideGrad"
    }
    with g.gradient_override_map(custom_grads):
        i = tf.identity(x, name="identity_" + str(uuid.uuid1()))
        ge = tf.greater_equal(x, 0, name="ge_" + str(uuid.uuid1()))
        # tf.stop_gradient is needed to exclude tf.to_float from derivative
        step_func = i + tf.stop_gradient(tf.to_float(ge) - i)
        return step_func

class HiddenPathways:
    # Initialize the class
    def __init__(self, t, S, layers, meal_tq):
        
        self.D = S.shape[1]
        
        self.t_min = t.min(0)
        self.t_max = t.max(0)
        
        self.S_mean = S.mean(0)
        self.S_std = self.D*[1.0]#S.std(0)
        
        
        # data on concentrations
        self.t = t
        self.S = S

        self.mt = 2.0*(meal_tq[0] - self.t_min)/(self.t_max - self.t_min) - 1.0
        self.mq = meal_tq[1]
        
        # layers
        self.layers = layers
        
        # initialize NN
        self.weights, self.biases = self.initialize_NN(layers)

#        self.k = tf.Variable(1.0/120.0, dtype=tf.float32, trainable=False)
#        self.Rm = tf.Variable(209.0, dtype=tf.float32, trainable=False)
        self.Vg = tf.Variable(10.0, dtype=tf.float32, trainable=False)
#        self.C1 = tf.Variable(300.0, dtype=tf.float32, trainable=False)
#        self.a1 = tf.Variable(6.6, dtype=tf.float32, trainable=False)
#        self.Ub = tf.Variable(72.0, dtype=tf.float32, trainable=False)
#        self.C2 = tf.Variable(144.0, dtype=tf.float32, trainable=False)
#        self.U0 = tf.Variable(4.0, dtype=tf.float32, trainable=False)
#        self.Um = tf.Variable(90.0, dtype=tf.float32, trainable=False)
#        self.C3 = tf.Variable(100.0, dtype=tf.float32, trainable=False)
#        self.C4 = tf.Variable(80.0, dtype=tf.float32, trainable=False)
        self.Vi = tf.Variable(11.0, dtype=tf.float32, trainable=False)
#        self.E = tf.Variable(0.2, dtype=tf.float32, trainable=False)
#        self.ti = tf.Variable(100.0, dtype=tf.float32, trainable=False)
#        self.beta = tf.Variable(1.772, dtype=tf.float32, trainable=False)
#        self.Rg = tf.Variable(180.0, dtype=tf.float32, trainable=False)
#        self.alpha = tf.Variable(7.5, dtype=tf.float32, trainable=False)
        self.Vp = tf.Variable(3.0, dtype=tf.float32, trainable=False)
#        self.C5 = tf.Variable(26.0, dtype=tf.float32, trainable=False)
#        self.tp = tf.Variable(6.0, dtype=tf.float32, trainable=False)
#        self.td = tf.Variable(12.0, dtype=tf.float32, trainable=False)

        self.logk = tf.Variable(-8.0, dtype=tf.float32, trainable=True)
        self.logRm = tf.Variable(0.0, dtype=tf.float32, trainable=True)
#        self.logVg = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logC1 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.loga1 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logUb = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logC2 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logU0 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logUm = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logC3 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logC4 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
#        self.logVi = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logE = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logti = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logbeta = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logRg = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logalpha = tf.Variable(0.0, dtype=tf.float32, trainable=True)
#        self.logVp = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logC5 = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logtp = tf.Variable(0.0, dtype=tf.float32, trainable=True)
        self.logtd = tf.Variable(0.0, dtype=tf.float32, trainable=True)

        
        self.var_list_eqns = [self.logk, self.logRm, self.logC1, self.loga1, self.logUb, 
                              self.logC2, self.logU0, self.logUm, self.logC3, self.logC4, 
                              self.logE, self.logbeta, self.logRg, self.logalpha, 
                              self.logC5, self.logti, self.logtp, self.logtd]#, self.logVi, self.logVp]
  
        self.k = tf.exp(self.logk)
        self.Rm = tf.exp(self.logRm)
#        self.Vg = tf.exp(self.logVg)
        self.C1 = tf.exp(self.logC1)
        self.a1 = tf.exp(self.loga1)
        self.Ub = tf.exp(self.logUb)
        self.C2 = tf.exp(self.logC2)
        self.U0 = tf.exp(self.logU0)
        self.Um = tf.exp(self.logUm)
        self.C3 = tf.exp(self.logC3)
        self.C4 = tf.exp(self.logC4)
#        self.Vi = tf.exp(self.logVi)
        self.E = tf.exp(self.logE)
        self.ti = tf.exp(self.logti)
        self.beta = tf.exp(self.logbeta)
        self.Rg = tf.exp(self.logRg)
        self.alpha = tf.exp(self.logalpha)
#        self.Vp = tf.exp(self.logVp)
        self.C5 = tf.exp(self.logC5)
        self.tp = tf.exp(self.logtp)
        self.td = tf.exp(self.logtd)

        # tf placeholders and graph
        self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
                                                     log_device_placement=True))
        
        # placeholders for data
        self.learning_rate = tf.placeholder(tf.float32, shape=[])
        self.t_tf = tf.placeholder(tf.float32, shape=[None, 1])
        self.S_tf = tf.placeholder(tf.float32, shape=[None, self.D])
        self.mt_tf = tf.placeholder(tf.float32, shape=[None, self.mt.shape[1]])
        self.mq_tf = tf.placeholder(tf.float32, shape=[None, self.mq.shape[1]])
        
        # placeholders for forward differentian
        self.dummy_tf = tf.placeholder(tf.float32, shape=(None, self.D)) # dummy variable for fwd_gradients (D outputs)
 
        # physics informed neural networks
        (self.S_pred,
         self.E_pred, self.IG) = self.net_HiddenPathways(self.t_tf, self.mt_tf, self.mq_tf)

        # loss
        self.loss_data = tf.reduce_mean(tf.square((self.S_tf[:,2:3] - self.S_pred[:,2:3])/self.S_std[2:3]))
        self.loss_eqns = tf.reduce_mean(tf.square(self.E_pred/self.S_std[:]))
        self.loss_auxl = tf.reduce_mean(tf.square((self.S_tf[-1,:]-self.S_pred[-1,:])/self.S_std[:]))
        self.loss = 0.999*self.loss_data + 0.001*self.loss_eqns + 0.001*self.loss_auxl
        
        # optimizers
        self.optimizer = tf.train.AdamOptimizer(learning_rate = self.learning_rate)
        self.optimizer_para = tf.train.AdamOptimizer(learning_rate = 0.001)

        self.train_op = self.optimizer.minimize(self.loss, var_list = self.weights + self.biases)
        self.trainpara_op = self.optimizer_para.minimize(self.loss, var_list = self.var_list_eqns)
#        self.grads, self.vars = zip(*self.optimizer_para.compute_gradients(self.loss,
#                                                                           var_list = self.var_list_eqns))
#        self.gradsnorm, _ = tf.clip_by_global_norm(self.grads, 1.0)
#        self.trainpara_op = self.optimizer_para.apply_gradients(zip(self.gradsnorm, self.vars))
        self.weights, _ = tf.clip_by_global_norm(self.weights, 1.0)

        init = tf.global_variables_initializer()
        self.sess.run(init)

    def initialize_NN(self, layers):
        weights = []
        biases = []
        num_layers = len(layers)
        for l in range(0,num_layers-1):
            W = self.xavier_init(size=[layers[l], layers[l+1]])
            b = tf.Variable(tf.zeros([1,layers[l+1]], dtype=tf.float32), dtype=tf.float32)
            weights.append(W)
            biases.append(b)
        return weights, biases
        
    def xavier_init(self, size):
        in_dim = size[0]
        out_dim = size[1]
        xavier_stddev = np.sqrt(2.0/(in_dim + out_dim))
        return tf.Variable(tf.truncated_normal([in_dim, out_dim], stddev=xavier_stddev), dtype=tf.float32)
    
    def neural_net(self, X, weights, biases):
        num_layers = len(weights) + 1
        
        H = X
        for l in range(0, num_layers-2):
            W = weights[l]
            b = biases[l]
            H = tf.matmul(H, W) + b
            H = H*tf.sigmoid(H)
        W = weights[-1]
        b = biases[-1]
        Y = tf.matmul(H, W) + b
        return Y
    
    def fwd_gradients(self, U, x):
        g = tf.gradients(U, x, grad_ys=self.dummy_tf)[0]
        return tf.gradients(g, self.dummy_tf)[0]
    
    def net_HiddenPathways(self, t, mt, mq):
        H = 2.0*(t - self.t_min)/(self.t_max - self.t_min) - 1.0
        S_tilde = self.neural_net(H, self.weights, self.biases)
        S = self.S[0,:] + self.S_std*(H + 1.0)*S_tilde
        
        intake = self.k * mq * heaviside(H-mt) * tf.exp(self.k*(mt-H)*(self.t_max-self.t_min)/2.0)
        IG = tf.reduce_sum(intake, axis=1, keepdims=True)
        kappa = 1.0/self.Vi + 1.0/(self.E*self.ti)
        f1 = self.Rm * tf.sigmoid(S[:,2:3]/(self.Vg*self.C1) - self.a1)
        f2 = self.Ub * (1.0 - tf.exp(-S[:,2:3]/(self.Vg*self.C2)))
        safe_log = tf.where(S[:,1:2] <= 0.0, tf.ones_like(S[:,1:2]), S[:,1:2])
        f3 = (self.U0 + self.Um*tf.sigmoid(self.beta*tf.log(kappa*safe_log/self.C4))) / (self.Vg*self.C3)
        f4 = self.Rg * tf.sigmoid(-self.alpha*(S[:,5:6]/(self.Vp*self.C5)-1.0))
                               
        F0 = f1 - self.E*(S[:,0:1]/self.Vp-S[:,1:2]/self.Vi) - S[:,0:1]/self.tp
        F1 = self.E*(S[:,0:1]/self.Vp-S[:,1:2]/self.Vi) - S[:,1:2]/self.ti
        F2 = f4 + IG - f2 - f3*S[:,2:3]
        F3 = (S[:,0:1] - S[:,3:4]) / self.td
        F4 = (S[:,3:4] - S[:,4:5]) / self.td
        F5 = (S[:,4:5] - S[:,5:6]) / self.td
        
        F = tf.concat([F0, F1, F2, F3, F4, F5], 1)

        S_t = self.fwd_gradients(S, t)
        
        E = S_t - F
        return S, E, IG
    
    def train(self, num_epochs, batch_size, learning_rate):

        for epoch in range(num_epochs):
            
            N = self.t.shape[0]
            perm = np.concatenate( (np.array([0]), np.random.permutation(np.arange(1,N-1)),
                                    np.array([N-1])) )
            
            start_time = time.time()
            for it in range(0, N, batch_size):
                idx = perm[np.arange(it,it+batch_size)]
                (t_batch,
                 S_batch,
                 mt_batch, mq_batch) = (self.t[idx,:],
                                        self.S[idx,:],
                                        self.mt[idx,:], self.mq[idx,:])
    
                tf_dict = {self.t_tf: t_batch, self.S_tf: S_batch,
                           self.mt_tf: mt_batch, self.mq_tf: mq_batch,
                           self.dummy_tf: np.ones((batch_size, self.D)),
                           self.learning_rate: learning_rate}
                
#                self.weights = self.sess.run(self.weightnorm)
                self.sess.run([self.train_op, self.trainpara_op], tf_dict)
                
                # Print
                if it % batch_size == 0:
                    elapsed = time.time() - start_time
                    [loss_data_value,
                     loss_eqns_value,
                     loss_auxl_value,
                     learning_rate_value] = self.sess.run([self.loss_data,
                                                           self.loss_eqns,
                                                           self.loss_auxl,
                                                           self.learning_rate], tf_dict)
                    print('Epoch: %d, It: %d, Loss Data: %.3e, Loss Eqns: %.3e, Loss Auxl: %.3e, Time: %.3f, Learning Rate: %.1e'
                          %(epoch, it/batch_size, loss_data_value, loss_eqns_value, loss_auxl_value, elapsed, learning_rate_value))
                    start_time = time.time()

    def predict(self, t_star, meal_tq):
        
        meal_tq[0] = 2.0*(meal_tq[0] - self.t_min)/(self.t_max - self.t_min) - 1.0
        tf_dict = {self.t_tf: t_star,
                   self.mt_tf: meal_tq[0], self.mq_tf: meal_tq[1],
                   self.dummy_tf: np.ones((t_star.shape[0], self.D))}
        
        S_star, IG = self.sess.run([self.S_pred, self.IG], tf_dict)
        S_star = np.append(S_star[:,:], IG[:], axis=1)
        return S_star

if __name__ == "__main__": 
    
    layers = [1] + 6*[6*30] + [6]

    meal_t = [300., 650., 1100., 2000.]
    meal_q = [60e3, 40e3, 50e3, 100e3]
    
    def intake(tn, k):
        def s(mjtj):
            return k*mjtj[1]*np.heaviside(tn-mjtj[0], 0.5)*np.exp(k*(mjtj[0]-tn))
        IG = np.array([s(mjtj) for mjtj in list(zip(meal_t, meal_q))]).sum()
        return IG
    
    # function that returns dx/dt
    def f(x, t): # x is 6 x 1
        k = 1./120.        
        Rm = 209.
        Vg = 10.
        C1 = 300.
        a1 = 6.6
        Ub = 72.
        C2 = 144.
        U0 = 4.
        Um = 90.
        C3 = 100.
        C4 = 80.
        Vi = 11.
        E = 0.2
        ti = 100.
        beta = 1.772
        Rg = 180.
        alpha = 7.5
        Vp = 3.
        C5 = 26.
        tp = 6.
        td = 12.
        
        kappa = 1.0/Vi + 1.0/E/ti
        f1 = Rm / (1.0 + np.exp(-x[2]/Vg/C1 + a1))
        f2 = Ub * (1.0 - np.exp(-x[2]/Vg/C2))
        f3 = (U0 + Um/(1.0+np.exp(-beta*np.log(kappa*x[1]/C4)))) / Vg / C3
        f4 = Rg / (1.0 + np.exp(alpha*(x[5]/Vp/C5-1.0)))
        
        x0 = f1 - E*(x[0]/Vp-x[1]/Vi) - x[0]/tp
        x1 = E*(x[0]/Vp-x[1]/Vi) - x[1]/ti
        x2 = f4 + intake(t, k) - f2 - f3*x[2]
        x3 = (x[0] - x[3]) / td
        x4 = (x[3] - x[4]) / td
        x5 = (x[4] - x[5]) / td
        
        X = np.array([x0, x1, x2, x3, x4, x5])
        return X
    
    # function that returns dx/dt
    def f_pred(x, t): # x is 6 x 1
        k = 0.008452
        Rm = 195.623553
        Vg = 10.000000
        C1 = 299.185109
        a1 = 6.577122
        Ub = 69.282806
        C2 = 99.703950
        U0 = 10.179196
        Um = 246.831083
        C3 = 267.665839
        C4 = 235.929227
        Vi = 4.260534
        E = 0.068354
        ti = 83.107742
        beta = 1.737333
        Rg = 182.453167
        alpha = 7.077085
        Vp = 1.030994
        C5 = 75.517887
        tp = 6.417090
        td = 11.976399
        
        kappa = 1.0/Vi + 1.0/E/ti
        f1 = Rm / (1.0 + np.exp(-x[2]/Vg/C1 + a1))
        f2 = Ub * (1.0 - np.exp(-x[2]/Vg/C2))
        f3 = (U0 + Um/(1.0+np.exp(-beta*np.log(kappa*x[1]/C4)))) / Vg / C3
        f4 = Rg / (1.0 + np.exp(alpha*(x[5]/Vp/C5-1.0)))
        
        x0 = f1 - E*(x[0]/Vp-x[1]/Vi) - x[0]/tp
        x1 = E*(x[0]/Vp-x[1]/Vi) - x[1]/ti
        x2 = f4 + intake(t, k) - f2 - f3*x[2]
        x3 = (x[0] - x[3]) / td
        x4 = (x[3] - x[4]) / td
        x5 = (x[4] - x[5]) / td
        
        X = np.array([x0, x1, x2, x3, x4, x5])
        return X

    def plotting(t_star, S_star, S_pred, perm, Vg2, forecast=False):
        sns.set()
    
        fig, ax = newfig(2.0, 0.7)
        gs0 = gridspec.GridSpec(1, 1)
        gs0.update(top=0.9, bottom=0.15, left=0.1, right=0.95, hspace=0.3, wspace=0.3)
        ax = plt.subplot(gs0[0:1, 0:1])
        ax.plot(t_star,S_star[:,2],'C1',linewidth=2,label='input data')
        ax.scatter(t_star[perm],S_star[perm,2],marker='o',s=40,label='sampled input')
        ax.set_xlabel('$t\ (min)$', fontsize=18)
        ax.set_ylabel('$G\ (mg/dl) $', fontsize=18)
        ax.legend(fontsize='large')
        
        ####################################    
        fig, ax = newfig(1.8, 0.75)
        gs1 = gridspec.GridSpec(1, 2)
        gs1.update(top=0.85, bottom=0.15, left=0.1, right=0.95, hspace=0.3, wspace=0.3)
        ax = plt.subplot(gs1[0:1, 0:1])
        ax.plot(t_star,S_star[:,0]*Vg2,'C1',linewidth=2,label='exact')
        ax.plot(t_star,S_pred[:,0]*Vg2,'g-.',linewidth=3,label='learned')
        ax.set_xlabel('$t\ (min)$', fontsize=18)
        ax.set_ylabel('$I_p\ (\mu U/ml)$', fontsize=18)
        ax.legend(fontsize='large')
        
        ax = plt.subplot(gs1[0:1, 1:2])
        ax.plot(t_star,S_star[:,1]*Vg2,'C1',linewidth=2)
        ax.plot(t_star,S_pred[:,1]*Vg2,'g-.',linewidth=3)
        ax.set_xlabel('$t\ (min)$', fontsize=18)
        ax.set_ylabel('$I_i\ (\mu U/ml)$', fontsize=18)
    
        fig, ax = newfig(1.8, 0.75)
        gs2 = gridspec.GridSpec(1, 2)
        gs2.update(top=0.85, bottom=0.15, left=0.1, right=0.95, hspace=0.3, wspace=0.3)
        ax = plt.subplot(gs2[0:1, 0:1])
        if not forecast:
            ax.scatter(t_star[perm],S_star[perm,2],marker='o',c='C1',s=30)
        else:
            ax.plot(t_star,S_star[:,2],'C1',linewidth=2)
        ax.plot(t_star,S_pred[:,2],'g-.',linewidth=3)
        ax.set_xlabel('$t\ (min)$', fontsize=18)
        ax.set_ylabel('$G\ (mg/dl)$', fontsize=18)
        
        ax = plt.subplot(gs2[0:1, 1:2])
        ax.plot(t_star,IG_star*Vg2,'C1',linewidth=2)
        ax.plot(t_star,S_pred[:,6]*Vg2,'g-.',linewidth=3)
        ax.set_xlabel('$t\ (min)$', fontsize=18)
        ax.set_ylabel('$I_G\ (mg/min)$', fontsize=18)
        

    # time points
    t_star = np.arange(0, 3000, 1.0)

    k = 1./120.
    Vp = 3.0
    Vi = 11.0
    Vg2 = 10.0*10.0
    S0 = 12.0*Vp
    S1 = 4.0*Vi
    S2 = 110.0*Vg2
    S3 = 0.0
    S4 = 0.0
    S5 = 0.0
    
    # initial condition
    x0 = np.array([S0, S1, S2, S3, S4, S5]).flatten()
    
    # solve ODE
    S_star = odeint(f, x0, t_star)
    S_star /= Vg2
    IG_star = np.array([intake(t, k) for t in t_star]) / Vg2

    t_train = t_star[:,None]
    S_train = S_star
    N_train = t_train.shape[0]
    N_perm = np.int32(N_train/4)
    perm = np.concatenate( (np.array([0]), np.random.randint(1, high=N_train-1, size=N_perm-2),
                            np.array([N_train-1])) )
    meal_tq = [np.array([N_perm*[x] for x in meal_t]).T,
               np.array([N_perm*[x/Vg2] for x in meal_q]).T]
    
    model = HiddenPathways(t_train[perm], S_train[perm,:], layers, meal_tq)

    model.train(num_epochs = 200000, batch_size = perm.shape[0], learning_rate = 1e-3)
    model.train(num_epochs = 100000, batch_size = perm.shape[0], learning_rate = 1e-4)
    model.train(num_epochs = 20000, batch_size = perm.shape[0], learning_rate = 1e-5)
#    model.train(num_epochs = 20000, batch_size = perm.shape[0], learning_rate = 1e-6)

    meal_tq = [np.array([N_train*[x] for x in meal_t]).T,
               np.array([N_train*[x/Vg2] for x in meal_q]).T]        
    # NN prediction
    S_pred = model.predict(t_star[:,None], meal_tq)
    plotting(t_star, S_star, S_pred, perm, Vg2)
    
    # Prediction based on inferred parameters
    k = 0.008452
    Vp = 1.030994
    Vi = 4.260534
    S0 = 12.0*Vp
    S1 = 4.0*Vi
    S2 = 110.0*Vg2
    S3 = 0.0
    S4 = 0.0
    S5 = 0.0
    x0 = np.array([S0, S1, S2, S3, S4, S5]).flatten()    
    S_pred = odeint(f_pred, x0, t_star)
    S_pred /= Vg2
    IG_pred = np.array([intake(t, k) for t in t_star]) / Vg2
    S_pred = np.append(S_pred[:,:], IG_pred[:,None], axis=1)
    plotting(t_star, S_star, S_pred, perm, Vg2, forecast=True)

    print('k =  %.6f' % ( model.sess.run(model.k) ) )
    print('Rm = %.6f' % ( model.sess.run(model.Rm)*Vg2 ) )
    print('Vg = %.6f' % ( model.sess.run(model.Vg) ) )
    print('C1 = %.6f' % ( model.sess.run(model.C1)*Vg2 ) )
    print('a1 = %.6f' % ( model.sess.run(model.a1) ) )
    print('Ub = %.6f' % ( model.sess.run(model.Ub)*Vg2 ) )
    print('C2 = %.6f' % ( model.sess.run(model.C2)*Vg2 ) )
    print('U0 = %.6f' % ( model.sess.run(model.U0)*Vg2 ) )
    print('Um = %.6f' % ( model.sess.run(model.Um)*Vg2 ) )
    print('C3 = %.6f' % ( model.sess.run(model.C3)*Vg2 ) )
    print('C4 = %.6f' % ( model.sess.run(model.C4)*Vg2 ) )
    print('Vi = %.6f' % ( model.sess.run(model.Vi) ) )
    print('E = %.6f' % ( model.sess.run(model.E) ) )
    print('ti = %.6f' % ( model.sess.run(model.ti) ) )
    print('beta = %.6f' % ( model.sess.run(model.beta) ) )
    print('Rg = %.6f' % ( model.sess.run(model.Rg)*Vg2 ) )
    print('alpha = %.6f' % ( model.sess.run(model.alpha) ) )
    print('Vp = %.6f' % ( model.sess.run(model.Vp) ) )
    print('C5 = %.6f' % ( model.sess.run(model.C5)*Vg2 ) )
    print('tp = %.6f' % ( model.sess.run(model.tp) ) )
    print('td = %.6f' % ( model.sess.run(model.td) ) )
    
    # savefig('./figures/Glycolytic', crop = False)