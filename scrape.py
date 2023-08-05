import argparse

from tqdm import tqdm
import numpy as np

from concurrent.futures import ThreadPoolExecutor

from tags import do_all_caption_post_process
from query import compose_query
import utils
import scrape_util
from scrape_util import (
    DanbooruScraper,
    ScrapeResultCache,
)
from scrape_config import (
    load_scrape_config,
    ScrapeConfig,
    QuerySubset,
    QueryListSubset,
    PostListSubset,
    CaptionConfig,
    CacheConfig,
)
from cache_util import load_search_cache, save_search_cache


def main(config: ScrapeConfig):
    print(config)

    # 事前の初期値設定
    if isinstance(config.caption, bool):
        if config.caption:
            config.caption = CaptionConfig()

    print("Starting scrape...")

    # このキャッシュは後ろのキャッシュとは別
    cache_config = (
        config.cache
        if isinstance(config.cache, CacheConfig)
        else CacheConfig()
        if config.cache == True
        else None
    )

    caches: list[ScrapeResultCache] = []

    for subset in config.subsets:
        if isinstance(subset, QuerySubset):
            print("Loading query...")
            scraper = DanbooruScraper(subset.domain or config.domain, config.auth)

            query = compose_query(
                subset.query, subset.search_filter, config.search_filter
            )
            print("Query: " + query)

            # キャッシュから
            posts = load_search_cache(subset.output_path, query)[: subset.limit]

            if posts is not None:
                print(f"Found {len(posts)} posts in cache")
            else:
                posts = scrape_util.get_posts(
                    scraper,
                    query,
                    subset.search_result_filter,
                    config.search_result_filter,
                    total_limit=subset.limit,
                    limit_per_page=200,
                )
                print(f"Found {len(posts)} posts")

                if cache_config is not None and cache_config.search_result:
                    save_search_cache(subset.output_path, query, posts)

            caches.append(ScrapeResultCache(posts, subset))
        elif isinstance(subset, QueryListSubset):
            print("Loading query list...")
            scraper = DanbooruScraper(subset.domain or config.domain, config.auth)
            queries = utils.load_file_lines(subset.query_list_file)

            for query in queries:
                query = compose_query(query, subset.search_filter, config.search_filter)

                print("Query: " + query)

                # キャッシュから
                posts = load_search_cache(subset.output_path, query)[: subset.limit]

                if posts is not None:
                    print(f"Found {len(posts)} posts in cache")
                else:
                    posts = scrape_util.get_posts(
                        scraper,
                        query,
                        subset.search_result_filter,
                        config.search_result_filter,
                        total_limit=subset.limit,
                        limit_per_page=200,
                    )

                    print(f"Found {len(posts)} posts")

                    if cache_config is not None and cache_config.search_result:
                        save_search_cache(subset.output_path, query, posts)

                caches.append(ScrapeResultCache(posts, subset))
        elif isinstance(subset, PostListSubset):
            print("Loading post urls...")
            post_urls = utils.load_file_lines(subset.post_url_list_file)

            print(f"Found {len(post_urls)} posts")

            posts = []

            for url in post_urls:
                domain, post_id = scrape_util.get_domain_and_post_id_from_url(url)
                scraper = DanbooruScraper(domain, config.auth)

                posts.append(scraper.get_post(post_id))

            caches.append(ScrapeResultCache(posts, subset))
        else:
            raise Exception("Invalid subset type")

    # caption post process
    print("Analyzing captions...")
    for cache in caches:
        for item in cache.items:
            if cache.caption is not None:
                item = do_all_caption_post_process(item, cache.caption)
            # fallback
            item = do_all_caption_post_process(item, config.caption)

    for cache in caches:
        chunks = np.array_split(cache.items, config.max_workers)

        print(f"Downloading {len(cache.items)} images...")

        with tqdm(total=len(cache.items)) as pbar:
            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                futures = []
                for chunk in chunks:
                    executor.submit(
                        scrape_util.save_from_cache,
                        chunk,
                        [cache] * len(chunk),
                        config,
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
