
import os

def analyze_sources():
    with open('docs/rick_rubin_sources.md', 'r') as f:
        sources = f.readlines()

    num_sources = len(sources)
    print(f"Number of sources: {num_sources}")

    with open('data/the_creative_act_full_content.txt', 'r') as f:
        book_content = f.read()

    word_count = len(book_content.split())
    print(f"Word count of 'The Creative Act': {word_count}")

if __name__ == "__main__":
    analyze_sources()
