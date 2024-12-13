import os
import yaml


def read_cfg(base_dir):
    path = os.path.join(base_dir, 'Cfg.yaml')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            Cfg = yaml.load(f.read(), Loader=yaml.FullLoader)
        off_Cfg = Cfg['offline']
        on_Cfg = Cfg['online']
        return off_Cfg, on_Cfg, Cfg
    else:
        raise FileNotFoundError('Cfg.yaml not found')
