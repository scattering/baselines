import tensorflow as tf
from baselines.common import tf_util
from baselines.a2c.utils import fc
from baselines.common.distributions import make_pdtype
from baselines.common.input import observation_placeholder, encode_observation
from baselines.common.tf_util import adjust_shape
from baselines.common.mpi_running_mean_std import RunningMeanStd
from baselines.common.models import get_network_builder
import numpy as np

import gym


class PolicyWithValue(object):
    """
    Encapsulates fields and methods for RL policy and value function estimation with shared parameters
    """

    def __init__(self, env, observations, latent, estimate_q=False, vf_latent=None, sess=None, **tensors):
        """
        Parameters:
        ----------
        env             RL environment

        observations    tensorflow placeholder in which the observations will be fed

        latent          latent state from which policy distribution parameters should be inferred

        vf_latent       latent state from which value function should be inferred (if None, then latent is used)

        sess            tensorflow session to run calculations in (if None, default session is used)

        **tensors       tensorflow tensors for additional attributes such as state or mask

        """

        self.X = observations
        print("x", self.X)
        self.state = tf.constant([])
        self.initial_state = None
        self.__dict__.update(tensors)
        self._action_mask_ph = tf.placeholder(dtype=tf.bool, shape=(5, 198),
                                                      name="action_mask_ph")
        vf_latent = vf_latent if vf_latent is not None else latent

        vf_latent = tf.layers.flatten(vf_latent)
        latent = tf.layers.flatten(latent)

        # Based on the action space, will select what probability distribution type
        self.pdtype = make_pdtype(env.action_space)
        #if isinstance(ac_space, Discrete):
        
        self.pd, self.pi = self.pdtype.pdfromlatent(latent, init_scale=0.01)

        # Take an action
        print("                     INIT                        INIT")
        self.action = self.pd.sample()
        print("WE HAVE SAMPLED                              WE HAVE SAMPLED                     WE HAVE SAMPLED")
        

        # Calculate the neg log of our probability
        self.neglogp = self.pd.neglogp(self.action)
        self.sess = sess or tf.get_default_session()

        if estimate_q:
            assert isinstance(env.action_space, gym.spaces.Discrete)
            self.q = fc(vf_latent, 'q', env.action_space.n)
            self.vf = self.q
        else:
            self.vf = fc(vf_latent, 'vf', 1)
            self.vf = self.vf[:,0]

    def _evaluate(self, variables, observation, action_mask = None, **extra_feed):
        #print("                             evaluating")
        #actions = tf.placeholder(shape=(1,), dtype=tf.float32)
        #masks = tf.placeholder(shape=(1,), dtype=tf.float32)
        #masked_actions = actions * masks
        #variables.insert(0, masked_actions)
        n_batch = 1
        #print("variables:               ", variables)
        mask = (observation[0] +1) % 2 
        sess = self.sess
        #if action_mask is None and isinstance(self.ac_space, Discrete):
        #print("action mask: ", action_mask)
        if action_mask is None:
            action_mask = np.ones((5, len(observation[0])), dtype=np.bool)
        #feed_dict = {actions: np.ones((len(observation[0]))), masks: np.array(mask), self.X: adjust_shape(self.X, observation)}
        #observation = np.zeros(2)
        feed_dict = {self.X: adjust_shape(self.X, observation), self._action_mask_ph: action_mask} #messing things up for other algs
        for inpt_name, data in extra_feed.items():
            if inpt_name in self.__dict__.keys():
                inpt = self.__dict__[inpt_name]
                if isinstance(inpt, tf.Tensor) and inpt._op.type == 'Placeholder':
                    feed_dict[inpt] = adjust_shape(inpt, data)
        #print("                               feed dict:", feed_dict)
        
        return sess.run(variables, feed_dict)
        
        
    def step(self, observation, action_mask=None, **extra_feed):
        """
        Compute next action(s) given the observation(s)

        Parameters:
        ----------

        observation     observation data (either single or a batch)

        **extra_feed    additional data such as state or mask (names of the arguments should match the ones in constructor, see __init__)

        Returns:
        -------
        (action, value estimate, next state, negative log likelihood of the action under current policy parameters) tuple
        """
        #print("                         in policies.step")
        #print("                         action: ", self.action)
        #count = 1
        #print("self.action:             ", self.action)
        #print("self.vf:                 ", self.vf)
        #print("self.state:              ", self.state)
        #print("self.neglop:             ", self.neglogp)
        #print("extra feed:              ", extra_feed)
         
        a, v, state, neglogp = self._evaluate([self.action, self.vf, self.state, self.neglogp], observation, **extra_feed)
        #if action_mask is not None and isinstance(self.ac_space, Discrete):
        #if action_mask is not None:
        a, v, state, neglogp = self._evaluate([self.action, self.vf, self.state, self.neglogp], observation, action_mask, **extra_feed)
        #else:
            #return self.sess.run([self.action, self.value_flat, self.snew, self.neglogp],
                                     #{self.obs_ph: obs, self.states_ph: state, self.dones_ph: mask})
             #a, v, state, neglogp = self._evaluate([self.action, self.vf, self.state, self.neglogp], observation, **extra_feed)
            
        
        print("action from _evaluate: ", a)
        
        #while observation[0][a] == 1 and len(set(observation[0])) != 1:
             #count += 1
             #a, v, state, neglogp = self._evaluate([masked_actions, self.vf, self.state, self.neglogp], observation, **extra_feed)
        #print("                         vf after evaluate: ", self.vf)
        #print("                         state after evaluate: ", self.state)
        #print("                         self.action after evaluate: ", self.action)
        #print(count)
        if state.size == 0:
            state = None
        return a, v, state, neglogp

    def value(self, ob, *args, **kwargs):
        """
        Compute value estimate(s) given the observation(s)

        Parameters:
        ----------

        observation     observation data (either single or a batch)

        **extra_feed    additional data such as state or mask (names of the arguments should match the ones in constructor, see __init__)

        Returns:
        -------
        value estimate
        """
        return self._evaluate(self.vf, ob, *args, **kwargs)

    def save(self, save_path):
        tf_util.save_state(save_path, sess=self.sess)

    def load(self, load_path):
        tf_util.load_state(load_path, sess=self.sess)

def build_policy(env, policy_network, value_network=None,  normalize_observations=False, estimate_q=False, **policy_kwargs):
    if isinstance(policy_network, str):
        network_type = policy_network
        policy_network = get_network_builder(network_type)(**policy_kwargs)

    def policy_fn(nbatch=None, nsteps=None, sess=None, observ_placeholder=None):
        ob_space = env.observation_space

        X = observ_placeholder if observ_placeholder is not None else observation_placeholder(ob_space, batch_size=nbatch)

        extra_tensors = {}

        if normalize_observations and X.dtype == tf.float32:
            encoded_x, rms = _normalize_clip_observation(X)
            extra_tensors['rms'] = rms
        else:
            encoded_x = X

        encoded_x = encode_observation(ob_space, encoded_x)

        with tf.variable_scope('pi', reuse=tf.AUTO_REUSE):
            policy_latent = policy_network(encoded_x)
            if isinstance(policy_latent, tuple):
                policy_latent, recurrent_tensors = policy_latent

                if recurrent_tensors is not None:
                    # recurrent architecture, need a few more steps
                    nenv = nbatch // nsteps
                    assert nenv > 0, 'Bad input for recurrent policy: batch size {} smaller than nsteps {}'.format(nbatch, nsteps)
                    policy_latent, recurrent_tensors = policy_network(encoded_x, nenv)
                    extra_tensors.update(recurrent_tensors)


        _v_net = value_network

        if _v_net is None or _v_net == 'shared':
            vf_latent = policy_latent
        else:
            if _v_net == 'copy':
                _v_net = policy_network
            else:
                assert callable(_v_net)

            with tf.variable_scope('vf', reuse=tf.AUTO_REUSE):
                # TODO recurrent architectures are not supported with value_network=copy yet
                vf_latent = _v_net(encoded_x)

        policy = PolicyWithValue(
            env=env,
            observations=X,
            latent=policy_latent,
            vf_latent=vf_latent,
            sess=sess,
            estimate_q=estimate_q,
            **extra_tensors
        )
        return policy

    return policy_fn


def _normalize_clip_observation(x, clip_range=[-5.0, 5.0]):
    rms = RunningMeanStd(shape=x.shape[1:])
    norm_x = tf.clip_by_value((x - rms.mean) / rms.std, min(clip_range), max(clip_range))
    return norm_x, rms

