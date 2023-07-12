import argparse

from tqdm import tqdm
import numpy as np

from concurrent.futures import ThreadPoolExecutor

from tags import do_all_caption_post_process
from query import compose_query
from scrape_util import (
    DanbooruScraper,
    ScrapeResultCache,
    get_posts,
    load_query_list_file,
    load_url_list_file,
    get_domain_and_post_id_from_url,
    process_post_cache,
)
from scrape_config import (
    load_scrape_config,
    ScrapeConfig,
    QuerySubset,
    QueryListSubset,
    PostListSubset,
    CaptionConfig,
)
from default_tags import DEFAULT_EXLUSION_META_TAGS


def main(config: ScrapeConfig):
    print(config)

    # 事前の初期値設定
    if isinstance(config.caption, bool):
        if config.caption:
            config.caption = CaptionConfig()

    print("Starting scrape...")

    caches: list[ScrapeResultCache] = []

    for subset in config.subsets:
        if isinstance(subset, QuerySubset):
            print("Loading query...")
            scraper = DanbooruScraper(subset.domain or config.domain)

            query = compose_query(subset.query, subset.filter, config.filter)
            print("Query: " + query)

            posts = get_posts(
                scraper,
                query,
                exclusion_general_tags=[],
                exclusion_meta_tags=DEFAULT_EXLUSION_META_TAGS,
                total_limit=subset.limit,
                limit_per_page=200,
            )

            print(f"Found {len(posts)} posts")

            caches.append(ScrapeResultCache(posts, subset))
        elif isinstance(subset, QueryListSubset):
            print("Loading query list...")
            scraper = DanbooruScraper(subset.domain or config.domain)
            queries = load_query_list_file(subset.query_list_file)

            for query in queries:
                print("Query: " + query)

                posts = get_posts(
                    scraper,
                    query,
                    exclusion_general_tags=[],
                    exclusion_meta_tags=DEFAULT_EXLUSION_META_TAGS,
                    total_limit=subset.limit,
                    limit_per_page=200,
                )

                print(f"Found {len(posts)} posts")

                caches.append(ScrapeResultCache(posts, subset))
        elif isinstance(subset, PostListSubset):
            print("Loading post urls...")
            post_urls = load_url_list_file(subset.post_url_list_file)

            print(f"Found {len(post_urls)} posts")

            posts = []

            for url in post_urls:
                domain, post_id = get_domain_and_post_id_from_url(url)
                scraper = DanbooruScraper(domain)

                posts.append(scraper.get_post(post_id))

            caches.append(ScrapeResultCache(posts, subset))
        else:
            raise Exception("Invalid subset type")

    # caption post process
    print("Analyzing captions...")
    for cache in caches:
        if cache.caption is not None:
            for item in cache.items:
                item = do_all_caption_post_process(item, cache.caption)
                item = do_all_caption_post_process(item, config.caption)

    print("Downloading images...")

    for cache in caches:
        chunks = np.array_split(cache.items, config.max_workers)

        with tqdm(total=len(cache.items)) as pbar:
            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                futures = []
                for chunk in chunks:
                    executor.submit(
                        process_post_cache,
                        chunk,
                        [cache] * len(chunk),
                        config.caption,
                        pbar,
                    )

                for future in futures:
                    future.result()

    print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape data from a website")
    parser.add_argument("config", help="The scrape config file")
    args = parser.parse_args()

    main(load_scrape_config(args.config))
