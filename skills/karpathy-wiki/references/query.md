# Query

When the user asks a question about the wiki's domain:

## Procedure

① **Read `index.md`** to identify relevant pages.

② **For wikis with 100+ pages**, also `search_files` across all `.md` files for key terms — the index alone may miss relevant content.

③ **Read the relevant pages** using `read_file`.

④ **Synthesize an answer** from the compiled knowledge. Cite the wiki pages you drew from: "根据 [[页面A]] 和 [[页面B]]……"

⑤ **File valuable answers back** — if the answer is a substantial 辨析 (comparison/distinction), deep dive, or novel synthesis, create a page in `queries/` or `comparisons/` or `synthesis/`. Don't file trivial lookups — only answers that would be painful to re-derive.

⑥ **Append to qa-log.md** — every query gets logged, regardless of whether it was filed:
```
## [YYYY-MM-DD] Q: 用户问题
A: 一句话摘要（来源：[[页面A]]、[[页面B]]）
```
`qa-log.md` is a complete chronological record of Q&A. `queries/` is curated highlights. Both serve different purposes — log everything, curate the best.

⑦ **Update log.md** with the query and whether it was filed.
