"""2021 tea-mapping feature image, extracted from the research workflow."""

import ee

SEASONS = ["win", "spr", "sum", "aut"]
CORE_INDICES = ["GRVI", "EVI", "NDRE1", "NDVI", "LSWI"]
SEASON_PAIRS = [("win", "sum"), ("win", "spr"), ("win", "aut"), ("sum", "spr"), ("sum", "aut"), ("spr", "aut")]
WINTER_RATIO_INDICES = ["GRVI", "EVI", "NDRE1"]
WINTER_RATIO_TARGETS = ["sum", "spr", "aut"]
PRIMARY_EXTRA_BANDS = ["DBNE_win", "BSI_win", "D_NDVI_spe_post", "D_NDRE1_spe_post", "D_BSI_post_spe", "VV", "VH", "VH_VV_diff", "B8_savg", "B8_ent", "Elevation", "Slope", "canopy_height"]
ALL_72_CANDIDATE_BANDS = ([f"{idx}_{s}" for s in SEASONS for idx in CORE_INDICES] + PRIMARY_EXTRA_BANDS + [f"D_{idx}_{s1}_{s2}" for s1, s2 in SEASON_PAIRS for idx in CORE_INDICES] + [f"R_{idx}_win_{st}" for st in WINTER_RATIO_TARGETS for idx in WINTER_RATIO_INDICES])


def _compute_5_core_indices(med_img):
    """
    在给定季节中值反射率影像 (已缩放至 0~1，包含 B2,B3,B4,B5,B8,B11) 上计算核心指数：
      GRVI, EVI, NDRE1, NDVI, LSWI, BSI, DBNE
    """
    b2 = med_img.select("B2")
    b3 = med_img.select("B3")
    b4 = med_img.select("B4")
    b5 = med_img.select("B5")
    b8 = med_img.select("B8")
    b11 = med_img.select("B11")

    grvi = b3.subtract(b4).divide(b3.add(b4).add(1e-6)).rename("GRVI")
    ndvi = b8.subtract(b4).divide(b8.add(b4).add(1e-6)).rename("NDVI")
    ndre1 = b8.subtract(b5).divide(b8.add(b5).add(1e-6)).rename("NDRE1")
    lswi = b8.subtract(b11).divide(b8.add(b11).add(1e-6)).rename("LSWI")

    evi = (
        med_img.expression(
            "2.5 * (b8 - b4) / (b8 + 6.0 * b4 - 7.5 * b2 + 1.0)",
            {"b8": b8, "b4": b4, "b2": b2},
        )
        .clamp(-1.0, 1.5)
        .rename("EVI")
    )

    bsi = (
        med_img.expression(
            "((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + 1e-6)",
            {"b11": b11, "b4": b4, "b8": b8, "b2": b2},
        )
        .rename("BSI")
    )
    dbne = ndvi.subtract(evi).rename("DBNE")

    return ee.Image.cat([b8.rename("B8"), grvi, evi, ndre1, ndvi, lswi, bsi, dbne])



def build_v5_feature_image(roi_geom, selected_bands=None, year=2023):
    """
    构建 V5/V6 全特征或指定优选波段子集的 GEE ee.Image（严格一致的云端计算图）。
    支持动态切换年份（如 year=2021 / 2022 / 2023 / 2024）。
    如果传入 selected_bands，则只拼接并输出所需的目标波段，大幅节省云端导出内存。
    """
    if selected_bands is None:
        selected_bands = ALL_72_CANDIDATE_BANDS

    next_year = year + 1
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    s2_clean = (
        s2.filterBounds(roi_geom)
        .filterDate(f"{year}-01-01", f"{next_year}-01-01")
        .linkCollection(cs, ["cs_cdf"])
        .map(
            lambda img: img.updateMask(img.select("cs_cdf").gte(0.58))
            .select(["B2", "B3", "B4", "B5", "B8", "B11"])
            .multiply(0.0001)
            .copyProperties(img, ["system:time_start"])
        )
    )

    annual_fallback = _compute_5_core_indices(s2_clean.median()).unmask(0.0)

    def season_comp(date_filter):
        raw_med = s2_clean.filter(date_filter).median()
        return _compute_5_core_indices(raw_med).unmask(annual_fallback)

    # 1. 春/夏/秋/冬 四季干净无重叠窗口
    win_c = season_comp(
        ee.Filter.Or(
            ee.Filter.date(f"{year}-01-01", f"{year}-03-01"),
            ee.Filter.date(f"{year}-11-20", f"{next_year}-01-01"),
        )
    )
    spr_c = season_comp(ee.Filter.date(f"{year}-03-01", f"{year}-06-01"))
    sum_c = season_comp(ee.Filter.date(f"{year}-06-01", f"{year}-09-01"))
    aut_c = season_comp(ee.Filter.date(f"{year}-09-01", f"{year}-11-20"))

    season_imgs = {"win": win_c, "spr": spr_c, "sum": sum_c, "aut": aut_c}

    band_dict = {}

    # 四季单季核心波段 (20 维)
    for s_name, s_img in season_imgs.items():
        for idx in CORE_INDICES:
            bname = f"{idx}_{s_name}"
            band_dict[bname] = s_img.select([idx], [bname])

    # 全配对 6 组季节差值 (30 维): 冬夏、冬春、冬秋、夏春、夏秋、春秋
    for s1, s2 in SEASON_PAIRS:
        for idx in CORE_INDICES:
            bname = f"D_{idx}_{s1}_{s2}"
            band_dict[bname] = (
                season_imgs[s1]
                .select(idx)
                .subtract(season_imgs[s2].select(idx))
                .rename(bname)
            )

    # 冬季锚定消影相对对比度 (9 维)
    for st in WINTER_RATIO_TARGETS:
        for idx in WINTER_RATIO_INDICES:
            bname = f"R_{idx}_win_{st}"
            i_win = win_c.select(idx)
            i_st = season_imgs[st].select(idx)
            denom = i_win.abs().add(i_st.abs()).add(0.05)
            band_dict[bname] = i_win.subtract(i_st).divide(denom).rename(bname)

    # 冬季阴影与裸土补充
    band_dict["DBNE_win"] = win_c.select(["DBNE"], ["DBNE_win"])
    band_dict["BSI_win"] = win_c.select(["BSI"], ["BSI_win"])

    # 春茶采前萌发 vs 采后重修剪脉冲（仅在需要时加入计算图）
    need_pruning = any(
        b in selected_bands
        for b in ["D_NDVI_spe_post", "D_NDRE1_spe_post", "D_BSI_post_spe"]
    )
    if need_pruning:
        spe_c = season_comp(ee.Filter.date(f"{year}-03-01", f"{year}-04-26"))
        post_c = season_comp(ee.Filter.date(f"{year}-04-26", f"{year}-06-06"))
        band_dict["D_NDVI_spe_post"] = (
            spe_c.select("NDVI").subtract(post_c.select("NDVI")).rename("D_NDVI_spe_post")
        )
        band_dict["D_NDRE1_spe_post"] = (
            spe_c.select("NDRE1").subtract(post_c.select("NDRE1")).rename("D_NDRE1_spe_post")
        )
        band_dict["D_BSI_post_spe"] = (
            post_c.select("BSI").subtract(spe_c.select("BSI")).rename("D_BSI_post_spe")
        )

    # 春季近红外 GLCM 纹理
    if any(b in selected_bands for b in ["B8_savg", "B8_ent"]):
        b8_quant = spr_c.select("B8").clamp(0.0, 1.0).multiply(100.0).toInt()
        glcm = b8_quant.glcmTexture(size=1)
        band_dict["B8_savg"] = glcm.select(["B8_savg"]).unmask(50.0)
        band_dict["B8_ent"] = glcm.select(["B8_ent"]).unmask(1.5)

    # Sentinel-1 C-SAR 年度中值
    if any(b in selected_bands for b in ["VV", "VH", "VH_VV_diff"]):
        s1 = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi_geom)
            .filterDate(f"{year}-01-01", f"{next_year}-01-01")
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .median()
        )
        vv = s1.select("VV").unmask(-10.0).rename("VV")
        vh = s1.select("VH").unmask(-17.0).rename("VH")
        band_dict["VV"] = vv
        band_dict["VH"] = vh
        band_dict["VH_VV_diff"] = vh.subtract(vv).rename("VH_VV_diff")

    # 地形与软冠层高度
    if any(b in selected_bands for b in ["Elevation", "Slope"]):
        dem = ee.Image("USGS/SRTMGL1_003")
        elev = dem.select("elevation").unmask(20.0).rename("Elevation")
        slope = ee.Terrain.slope(elev).rename("Slope")
        band_dict["Elevation"] = elev
        band_dict["Slope"] = slope

    if "canopy_height" in selected_bands:
        canopy = (
            ee.Image("users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1")
            .select(["b1"], ["canopy_height"])
            .unmask(10.0)
        )
        band_dict["canopy_height"] = canopy

    out_bands = [band_dict[b].toFloat() for b in selected_bands]
    return ee.Image.cat(out_bands).select(selected_bands)

