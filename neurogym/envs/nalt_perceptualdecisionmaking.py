#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
from gym import spaces
import neurogym as ngym


class nalt_PerceptualDecisionMaking(ngym.PeriodEnv):
    """N-alternative perceptual decision-making.

    N-alternative forced choice task in which the subject has
    to integrate N stimuli to decide which one is higher on average.

    Args:
        stim_scale: Controls the difficulty of the experiment. (def: 1., float)
        n_ch: Number of choices. (def: 3, int)
    """
    metadata = {
        'paper_link': None,
        'paper_name': None,
        'tags': ['perceptual', 'n-alternative', 'supervised']
    }

    def __init__(self, dt=100, rewards=None, timing=None, stim_scale=1.,
                 sigma=1.5, n_ch=3):
        super().__init__(dt=dt)
        self.n = n_ch
        self.choices = np.arange(n_ch) + 1
        # cohs specifies the amount of evidence (which is modulated by stim_scale)
        self.cohs = np.array([0, 6.4, 12.8, 25.6, 51.2])*stim_scale
        self.sigma = sigma / np.sqrt(self.dt)  # Input noise

        # Rewards
        self.rewards = {'abort': -0.1, 'correct': +1., 'fail': 0.}
        if rewards:
            self.rewards.update(rewards)
        self.timing = {
            'fixation': ('constant', 500),
            'stimulus': ('truncated_exponential', [330, 80, 1500]),
            'decision': ('constant', 500)}
        if timing:
            self.timing.update(timing)

        self.abort = False
        # action and observation spaces
        self.action_space = spaces.Discrete(n_ch+1)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(n_ch+1,),
                                            dtype=np.float32)
        self.ob_dict = {'fixation': 0, 'stimulus': range(1, n_ch+1)}

    def new_trial(self, **kwargs):
        """
        new_trial() is called when a trial ends to generate the next trial.
        The following variables are created:
            ground_truth: correct response for the trial
            coh: stimulus coherence (evidence) for the trial
            ob: observation
        """
        # ---------------------------------------------------------------------
        # Trial
        # ---------------------------------------------------------------------
        self.trial = {
            'ground_truth': self.rng.choice(self.choices),
            'coh': self.rng.choice(self.cohs),
        }
        self.trial.update(kwargs)

        self.add_period(['fixation', 'stimulus', 'decision'], after=0, last_period=True)

        self.add_ob(1, 'fixation', where='fixation')
        stim = np.ones(self.n) * (1 - self.trial['coh']/100)/2
        stim[self.trial['ground_truth'] - 1] = (1 + self.trial['coh']/100)/2
        self.add_ob(stim, 'stimulus', where='stimulus')
        self.add_randn(0, self.sigma, 'stimulus')

        self.set_groundtruth(self.trial['ground_truth'], 'decision')

    def _step(self, action, **kwargs):
        """
        _step receives an action and returns:
            a new observation, obs
            reward associated with the action, reward
            a boolean variable indicating whether the experiment has end, done
            a dictionary with extra information:
                ground truth correct response, info['gt']
                boolean indicating the end of the trial, info['new_trial']
        """
        # ---------------------------------------------------------------------
        # Reward and observations
        # ---------------------------------------------------------------------
        new_trial = False

        obs = self.ob_now
        gt = self.gt_now

        reward = 0
        if self.in_period('fixation'):
            if action != 0:
                new_trial = self.abort
                reward = self.rewards['abort']
        elif self.in_period('decision'):
            if action != 0:
                new_trial = True
                if action == gt:
                    reward = self.rewards['correct']
                    self.performance = 1
                else:
                    reward = self.rewards['fail']

        return obs, reward, False, {'new_trial': new_trial, 'gt': gt}


if __name__ == '__main__':
    env = nalt_PerceptualDecisionMaking()
    ngym.utils.plot_env(env)
