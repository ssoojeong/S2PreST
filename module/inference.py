import argparse, os, sys, glob
import PIL
import torch
import torch.nn as nn
import numpy as np
from omegaconf import OmegaConf
from PIL import Image
from tqdm import tqdm, trange
from itertools import islice
from einops import rearrange, repeat
from torchvision.utils import make_grid
from torch import autocast
from contextlib import nullcontext
import time
from pytorch_lightning import seed_everything

sys.path.append(os.path.dirname(sys.path[0]))
from ldm.util import instantiate_from_config
from ldm.models.diffusion.ddim import DDIMSampler
from ldm.models.diffusion.plms import PLMSSampler

from transformers import CLIPProcessor, CLIPModel

from kornia_canny.kornia_canny import save_canny

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


def load_model_from_config(config, ckpt, verbose=False):
    print(f"Loading model from {ckpt}")
    pl_sd = torch.load(ckpt, map_location="cpu")
    if "global_step" in pl_sd:
        print(f"Global Step: {pl_sd['global_step']}")
    sd = pl_sd["state_dict"]
    model = instantiate_from_config(config.model)
    m, u = model.load_state_dict(sd, strict=False)
    if len(m) > 0 and verbose:
        print("missing keys:")
        print(m)
    if len(u) > 0 and verbose:
        print("unexpected keys:")
        print(u)

    model.to(device)
    model.eval()
    return model

def image_resize(resize_from_path, resize_image):
    image = Image.open(resize_from_path).convert("RGB")
    w, h = image.size
    resize_image = resize_image.resize((w, h), resample=PIL.Image.LANCZOS)
    return resize_image

def load_img(path):
    image = Image.open(path).convert("RGB")
    w, h = image.size
    print(f"loaded input image of size ({w}, {h}) from {path}")
    w, h = map(lambda x: x - x % 32, (w, h))  # resize to integer multiple of 32
    image = image.resize((512, 512), resample=PIL.Image.LANCZOS)
    image = np.array(image).astype(np.float32) / 255.0
    image = image[None].transpose(0, 3, 1, 2)
    image = torch.from_numpy(image)
    return 2.*image - 1.

def main(prompt = '', content_dir = '', style_dir='', ddim_steps = 50, strength = 0.5, model = None, sampler=None, seed=42, save_path=None):
    #content_dir = os.path.join(content_dir, os.listdir(content_dir)[0])
    save_path = os.path.join(save_path, f'wt_{str(strength)}')
    os.makedirs(save_path, exist_ok=True)
    
    style_dir = os.path.join(style_dir, os.listdir(style_dir)[0])
    
    savepath_ca = os.path.join(save_path, 'canny')
    os.makedirs(savepath_ca, exist_ok=True)
    canny_dir = save_canny(content_dir, savepath_ca)
    
    ddim_eta=0.0
    n_iter=1
    C=4
    f=8
    n_samples=1
    n_rows=0
    scale=10.0
    
    precision="autocast"
    seed_everything(seed)

    batch_size = n_samples
    n_rows = n_rows if n_rows > 0 else batch_size
    data = [batch_size * [prompt]]
    
    style_image = load_img(style_dir).to(device)
    style_image = repeat(style_image, '1 ... -> b ...', b=batch_size)
    style_latent = model.get_first_stage_encoding(model.encode_first_stage(style_image))  # move to latent space

    content_name =  content_dir.split('/')[-1].split('.')[0]
    content_image = load_img(content_dir).to(device)
    content_image = repeat(content_image, '1 ... -> b ...', b=batch_size)
    content_latent = model.get_first_stage_encoding(model.encode_first_stage(content_image))  # move to latent space

    init_latent = content_latent

    canny_image = load_img(canny_dir).to(device)
    canny_image = repeat(canny_image, '1 ... -> b ...', b=batch_size)
    canny_latent = model.get_first_stage_encoding(model.encode_first_stage(canny_image))  # move to latent space
    
    sampler.make_schedule(ddim_num_steps=ddim_steps, ddim_eta=ddim_eta, verbose=False)

    assert 0. <= strength <= 1., 'can only work with strength in [0.0, 1.0]'
    t_enc = int(strength * ddim_steps)
    print(f"target t_enc is {t_enc} steps")

    precision_scope = autocast if precision == "autocast" else nullcontext
    with torch.no_grad():
        with precision_scope("cuda"):
            with model.ema_scope():
                tic = time.time()
                all_samples = list()
                for n in trange(n_iter, desc="Sampling"):
                    for prompts in tqdm(data, desc="data"):
                        uc = None
                        if scale != 1.0:
                            uc = model.get_learned_conditioning(batch_size * [""], style_image)
                            uc_con = model.get_learned_conditioning(batch_size * [""], content_image)
                            uc_can = model.get_learned_conditioning(batch_size * [""], canny_image)
                            uc_con_can = uc_con * 0.2 + uc_can * 0.8
                        if isinstance(prompts, tuple):
                            prompts = list(prompts)

                        c= model.get_learned_conditioning(prompts, style_image)
                        c_con= model.get_learned_conditioning(prompts, content_image)
                        c_can= model.get_learned_conditioning(prompts, canny_image)
                        ab = 0.5
                        c_con_can = c_con * ab + c_can * (1-ab)
                        c_o_con_can = c_con * 0.3 + c_can * 0.3 + c * 0.4

                        t_enc = int(strength * 1000) 

                        alpha = 0.7
                        alpha_2 = 0.5
                        init_latent_mix_content = content_latent*alpha + style_latent*(1-alpha)

                        x_noisy_content = model.q_sample(x_start=init_latent, t=torch.tensor([t_enc]*batch_size).to(device))
                        x_noisy_canny = model.q_sample(x_start=canny_latent, t=torch.tensor([t_enc]*batch_size).to(device))
                        x_noisy = x_noisy_content * alpha_2 + x_noisy_canny * alpha_2
                        model_output = model.apply_model(x_noisy, torch.tensor([t_enc]*batch_size).to(device), c_con_can)
                        z_enc = sampler.stochastic_encode(init_latent_mix_content, torch.tensor([t_enc]*batch_size).to(device),\
                                                          noise = model_output, use_original_steps = True)
                
                        t_enc = int(strength * ddim_steps)
                        samples = sampler.decode(z_enc, c_con_can, t_enc, 
                                                unconditional_guidance_scale=scale,
                                                 unconditional_conditioning=uc_con_can,)

                        x_samples = model.decode_first_stage(samples)
                        x_samples = torch.clamp((x_samples + 1.0) / 2.0, min=0.0, max=1.0)

                        for x_sample in x_samples:
                            x_sample = 255. * rearrange(x_sample.cpu().numpy(), 'c h w -> h w c')
                        all_samples.append(x_samples)

                # additionally, save as grid
                grid = torch.stack(all_samples, 0)
                grid = rearrange(grid, 'n b c h w -> (n b) c h w')
                grid = make_grid(grid, nrow=n_rows)

                # to image
                grid = 255. * rearrange(grid, 'c h w -> h w c').cpu().numpy()
                output = Image.fromarray(grid.astype(np.uint8))
                output = image_resize(content_dir, output)
                if save_path is not None:
                    final_save_path = os.path.join(save_path, 'stylized')
                    os.makedirs(final_save_path, exist_ok=True)
                    output.save(os.path.join(final_save_path, f'{content_name}.png'))

                toc = time.time()
    return output



def get_parser(**parser_kwargs):
    def str2bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ("yes", "true", "t", "y", "1"):
            return True
        elif v.lower() in ("no", "false", "f", "n", "0"):
            return False
        else:
            raise argparse.ArgumentTypeError("Boolean value expected.")

    parser = argparse.ArgumentParser(**parser_kwargs)
    parser.add_argument(
        "--style_guidance",
        type=float,
        default=0.4,
    )
    parser.add_argument(
        "--content_path",
        type=str,
        default='dataset/face/img/060002_4_028450_FEMALE_30.jpg'
    )
    parser.add_argument(
        "--style_name",
        type=str,
        default='wiki_1'
    )
    parser.add_argument(
        "--style_dir",
        type=str,
        default='dataset'
    )
    parser.add_argument(
        "--style_emb",
        type=str,
        default='module/logs'
    )
    parser.add_argument(
        "--save_dir",
        type=str,
        default='results'
    )

    return parser
           
                          
if __name__ == "__main__":
    parser = get_parser()
    opt, unknown = parser.parse_known_args()
    
    #모델 호출
    config="module/configs/stable-diffusion/v1-inference.yaml"
    ckpt="module/models/sd/sd-v1-4.ckpt"
    config = OmegaConf.load(f"{config}")
    model = load_model_from_config(config, f"{ckpt}")
    sampler = DDIMSampler(model)
                    
    style_dir = os.path.join(opt.style_dir, opt.style_name)  
    save_dir = os.path.join(opt.save_dir, opt.style_name)    
    style_emb_path = os.path.join(opt.style_emb, opt.style_name)    
    style_emb_pt_path = style_emb_path+'/checkpoints/embeddings.pt'
    
    model.embedding_manager.load(style_emb_pt_path)
    model = model.to(device)
    
    main(prompt = '*', \
            content_dir = opt.content_path, \
            style_dir = style_dir, \
            ddim_steps = 50, \
            strength = opt.style_guidance, \
            seed=42, \
            model = model,
            sampler = sampler,
            save_path=save_dir,
            )