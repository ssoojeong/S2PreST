# Style Transfer: Mine


### 1. Save files
- ckpt: ".module/models/sd/sd-v1-4.ckpt." [Stable Diffusion Model](https://huggingface.co/CompVis/stable-diffusion-v-1-4-original/resolve/main/sd-v1-4.ckpt)
- dataset: "./dataset/face" [Face Dataset](https://www.kaggle.com/datasets/tapakah68/face-segmentation?resource=download)
- logs: "./module/logs" [Pretrained logs](https://drive.google.com/drive/folders/1dpzxAPRQE__UuQahH2jSu-JXVcmlAQTW?usp=sharing)

### 2. Create Environment
  ```sh
    cd ./sing
    conda env create -f environment.yaml
    conda activate ldm
  ```

### 3. Inference

  ```sh
    cd ./sing
  
    python ./module/inference.py \
             --style_name='wiki_1' \
             --content_path /path/to/directory/with/images
  ```

  ```sh
    cd ./sing
  
    python ./module/inference.py \
             --style_name='wiki_2' \
             --content_path /path/to/directory/with/images
  ```

### 4. Results

- stylized image: "./results/{style_name}/wt_{style_guidance_weight}/stylized/{content_image_name}"
- canny image: "./results/{style_name}/wt_{style_guidance_weight}/canny/canny.png"
