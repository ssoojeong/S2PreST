#canny edge 만드는 코드
import kornia as K
from kornia.core import Tensor
from PIL import Image

import cv2
import matplotlib.pyplot as plt
from einops import rearrange, repeat
import os


def edge_detection(filepath): 
        img: Tensor = K.io.load_image(filepath, K.io.ImageLoadType.RGB32)
        img = img[None]
        x_gray = K.color.rgb_to_grayscale(img)
        x_canny: Tensor = K.filters.canny(x_gray)[0]
        output = K.utils.tensor_to_image(1. - x_canny.clamp(0., 1.0))
        
        return output
    

def save_canny(contentpath, savepath, name='canny.png'):
    output = edge_detection(contentpath)
    output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
    plt.imshow(output)
    plt.axis('off')
    savepath = os.path.join(savepath, f'{name}')
    plt.savefig(savepath, bbox_inches='tight', pad_inches=0)
    with Image.open(savepath) as im:
        # Create a thumbnail of the image
        im.thumbnail((512, 512))
        # Save the thumbnail
        im.save(savepath)
    return savepath