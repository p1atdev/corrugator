# Danbooru scraping tool

This tool is under construction, so it may be buggy.

## Setup

```
pip install -r requirements.txt
```

## Example usages

You need to write config file to scrape. Yaml file is highly recommended because very readable, but JSON and TOML are also supported.

### Just simple

Search for `1girl cat_ears score:50..100` up to 20 posts and `1girl cat_ears score:>100` up to 50 posts, and save only images to `./output/cat ears` for the former, save images with captions for the latter.


```yaml
subsets:
  - query: "1girl cat_ears score:50..100"
    output_path: "./output/cat ears/high quality"
    limit: 20
    caption: false
  - query: "1girl cat_ears score:>100"
    output_path: "./output/cat ears/best quality"
    limit: 50
    caption: true
```

```bash
python ./scrape.py ./example/simple.yaml
```

### Using query list

Search for queries in `./example/query_list.txt` and save images up to 50 images for each query. When searching, `filetype:png,jpg,webp` is added to each query.

When downloading images, 10 workers are used for multithreaded download. (If not specified, 4 workers are used.)

```yaml
domain: "danbooru.donmai.us" # or safebooru.donmai.us

subsets:
  - query_list_file: "./example/query_list.txt"
    output_path: "./output/query_list_example"
    limit: 50

    caption: false 

search_filter:
  filetypes:
    - png
    - jpg
    - webp
    # - gif

max_workers: 10
```

### Post processing

Customize captions to save.

Search for `cat_ears` and filter it only includes `solo` and does not include `2girls` and `3girls`, and save up to 50 images.

When saving captions, artist tags and copyright tags are not used, character tags, general tags and meta tags are used. However, the `cat ears` tag in general tags will be replaced with `nekomimi`, meta tags will be removed except for the tags specified in `./config/allowed_meta_tags.txt`.


```yaml
subsets:
  - query: "cat_ears"
    output_path: "./output/post_processes"
    limit: 50

caption:
  artist: false
  copyright: false
  character: true
  general:
    replaces:
      - tags: ["cat ears"]
        to: "nekomimi"
  meta:
    keeps:
      - tags: "./config/allowed_meta_tags.txt" # delete all tags except these tags

search_result_filter:
  include_any: ["solo"]
  exclude_any: ["2girls", "3girls"]

max_workers: 4
```




