

vitmoe_setting = dict(
    img_size=(256, 192),
    patch_size=16,
    embed_dim=768,
    depth=12,
    num_heads=12,
    ratio=1,
    use_checkpoint=False,
    mlp_ratio=4,
    qkv_bias=True,
    drop_path_rate=0.3,
    num_expert=6,
    part_features=192
)

coco17_head_setting = dict(
    in_channels=768,
    out_channels=17,
    num_deconv_layers=2,
    num_deconv_filters=(256, 256),
    num_deconv_kernels=(4, 4)
)

coco133_head_setting = dict(
    in_channels=768,
    out_channels=133,
    num_deconv_layers=2,
    num_deconv_filters=(256, 256),
    num_deconv_kernels=(4, 4)
)