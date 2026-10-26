"""Shared two-state Kalman reference; no language model numerical inference."""
import math
from .world import transition

class Kalman:
    def __init__(self, omega=.8, damping=.015, process_noise=.008):
        self.x,self.v,self.p,self.q,self.r = 1.,0.,.04,0.,.16
        self.omega,self.damping,self.process_noise = omega,damping,process_noise
        self.at=0.
        self.last_observation=None
        self.innovation=None

    def forecast(self, dt):
        a,b,c,d=transition(self.omega,self.damping,dt)
        p=a*a*self.p+2*a*b*self.q+b*b*self.r+self.process_noise*dt
        q=a*c*self.p+(a*d+b*c)*self.q+b*d*self.r
        r=c*c*self.p+2*c*d*self.q+d*d*self.r+self.process_noise*dt
        return a*self.x+b*self.v,c*self.x+d*self.v,max(1e-12,p),q,max(1e-12,r)

    def propagate(self, at):
        if at < self.at:
            raise ValueError('monotonic estimator time required')
        self.x,self.v,self.p,self.q,self.r=self.forecast(at-self.at)
        self.at=at

    def update(self, observation):
        if observation['measured_at'] != self.at:
            return 'stale-rejected'
        residual=observation['value']-self.x
        s=self.p+observation['noise_std']**2
        self.innovation=residual/math.sqrt(s)
        # Reject gross contradictory values, but keep residual as detection evidence.
        if abs(self.innovation)>8:
            return 'contradiction-rejected'
        kx,kv=self.p/s,self.q/s
        p,q,r=self.p,self.q,self.r
        self.x += kx*residual
        self.v += kv*residual
        self.p=max(1e-12,p-kx*p)
        self.q=q-kx*q
        self.r=max(1e-12,r-kv*q)
        self.last_observation=self.at
        return 'succeeded'

    def public(self):
        return {'at':self.at,'x':self.x,'v':self.v,'std':math.sqrt(self.p),'variance':self.p,
                'last_observation':self.last_observation,'innovation':self.innovation}
