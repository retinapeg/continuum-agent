from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    provider: str
    model: str
    task_classes: tuple[str,...]
    reliability: float
    verified: bool


class Router:
    def __init__(self, routes, fixed=None):
        self.routes, self.fixed = routes, fixed

    def choose(self, task_class, attempt=0, prior_checkpoint=None, known_unsent=True):
        eligible = [r for r in self.routes if r.verified and task_class in r.task_classes]
        if attempt and not known_unsent:
            raise ValueError('outcome-unknown requests cannot be automatically routed again')
        if self.fixed:
            eligible = [r for r in eligible if (r.provider,r.model)==self.fixed]
        eligible.sort(key=lambda r:(-r.reliability,r.provider,r.model))
        if not eligible:
            raise ValueError('no verified configured route')
        chosen = eligible[min(attempt,len(eligible)-1)]
        return chosen, {'reason':'fixed_scientific_comparison' if self.fixed else 'verified_task_support_then_measured_reliability',
                        'candidates':[r.__dict__ for r in eligible], 'chosen':chosen.__dict__,
                        'fallback':bool(attempt),'attempt_index':attempt,'prior_checkpoint':prior_checkpoint}


class RoutedProvider:
    """Operational routing only. Main scientific campaigns use fixed CLIProvider."""
    name,model='router','configured-rules-v1'
    def __init__(self,config,work):
        from .providers import CLIProvider
        self.config=config
        self.routes=[];self.providers={}
        for item in config['models']:
            attempts=item['measured_attempts'];successes=item['measured_valid_responses']
            if not 0<=successes<=attempts:raise ValueError('invalid measured routing counts')
            reliability=(successes+1)/(attempts+2)
            route=Route(item['provider'],item['model'],tuple(item['task_classes']),reliability,item['live_verified'])
            self.routes.append(route)
            self.providers[(route.provider,route.model)]=CLIProvider(route.provider,route.model,work/route.model)
        self.router=Router(self.routes)
    def propose(self,context,cancel,progress):
        from .providers import ProviderError
        task_class='document' if context.get('documents') or any('brief' in g['title'].lower() or 'document' in g['title'].lower() for g in context.get('goals',[])) else 'conversation'
        maximum=2 if self.config.get('allow_known_unsent_fallback',False) else 1
        for attempt in range(maximum):
            selected,receipt=self.router.choose(task_class,attempt,context.get('now'),known_unsent=True)
            receipt['reliability_estimator']='(measured_valid_responses+1)/(measured_attempts+2)'
            progress({'type':'routing.selected',**receipt})
            try:return self.providers[(selected.provider,selected.model)].propose(context,cancel,progress)
            except ProviderError as exc:
                if not exc.known_unsent or attempt+1>=maximum:raise
                progress({'type':'routing.known_unsent','error':str(exc),'attempt_index':attempt})
