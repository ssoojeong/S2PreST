# S2PreST: Semantic-Shape-Guided Style Transfer in Inversion-Based Diffusion for Source Images Preservation

![samples](figure/samples.png)

Image style transfer using diffusion-based methods has focused on generating high-quality results and has become popular in various industrial domains, such as entertainment and digital arts. Although the previous methods have generated great results, they still have some limitations in
transferring the style of the reference image to the detailed semantic shapes of the source image, leading to significant distortions in some regions. Thus, in this paper, we introduce an additional framework that extracts the Canny edge map from the source image and re-optimizes the style features from the reference image with the semantic features from the source image and its Canny edge map. Also these features are efficiently combined using linear interpolation and applied to the diffusion denoising process without additional fine-tuning. Experimental results demonstrate the ability to transfer style to the semantic shapes of the source image both quantitatively and qualitatively.

---
## Getting Started
### 1. Saved Files
- ckpt: ".module/models/sd/sd-v1-4.ckpt." [Stable Diffusion Model](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original/resolve/main/sd-v1-4.ckpt)
- dataset: "./dataset/face" [Face Dataset](https://www.kaggle.com/datasets/tapakah68/face-segmentation?resource=download)
- logs: "./module/logs" [Pretrained logs](https://drive.google.com/drive/folders/1dpzxAPRQE__UuQahH2jSu-JXVcmlAQTW?usp=sharing)

### 2. Create Environment
  ```sh
    conda env create -f environment.yaml
    conda activate ldm
  ```

### 3. Inference

  ```sh
  
    python ./module/inference.py \
             --style_name='wiki_1' \
             --content_path /path/to/directory/with/images
  ```

  ```sh

    python ./module/inference.py \
             --style_name='wiki_2' \
             --content_path /path/to/directory/with/images
  ```

### 4. Results

- stylized image: "./results/{style_name}/wt_{style_guidance_weight}/stylized/{content_image_name}"
- canny image: "./results/{style_name}/wt_{style_guidance_weight}/canny/canny.png"

---

## Comparison Data
- Qualitative results with zoomed-in views of specific square regions from each first row. Columns 3 to 8 present image-to-image stylized results without context-aware text conditioning, while columns 9 to 11 present text-description-guided stylized results.
![samples](figure/comparison.jpg)

- Qualitative comparison with close-up views of stylized images from four types of source images.
![samples](figure/comparison2.png)
