# Open Skill Standard (tiếng Việt)

**Một router, một skill graph, 28 vai trò IT.** Đây là một chuẩn mở, không phụ thuộc agent, để chọn đúng Agent Skill cho từng việc. Repo kèm bản triển khai tham chiếu, nối các bộ superpowers, BMad Method, spec-kit, codegraph, skill của Anthropic và nhiều nguồn khác mà không sao chép nội dung của bộ nào.

[English](README.md) · **Tiếng Việt**

[Website](https://vokhoinhon.github.io/open-skill-standard/vi/) · [Đặc tả](spec/SPEC.md) · [Đóng góp](CONTRIBUTING.md)

<img src=".github/assets/route-data.svg" alt="Terminal: open-skill route --explain cho data engineer thêm pipeline vào warehouse trả về một chuỗi có thứ tự và có giải thích: writing-plans, subagent-driven-development, explore-data, code-review, kèm điểm, ứng viên xếp sau và lệnh cài cho từng skill còn thiếu" width="790">

## Vì sao cần

Agent lập trình ngày nay nạp skill từ rất nhiều dự án độc lập. Một máy thường có hơn 100 skill trùng chức năng: ba quy trình build, vài kiểu review, hai kiểu brainstorm. Có hai thực tế gây khó:

- Agent chọn skill bằng cách so khớp mô tả. Mô tả trùng nhau khiến nó nạp sai skill hoặc bỏ sót skill đúng.
- Claude Code chỉ dành khoảng 1% context cho danh sách skill, và cắt mô tả của skill ít dùng trước ([tài liệu](https://code.claude.com/docs/en/skills)). Vì vậy càng cài nhiều skill, việc chọn càng kém.

Open Skill Standard bổ sung lớp thông tin còn thiếu: mỗi skill phục vụ **vai trò nào**, hoạt động ở **giai đoạn (phase) nào**, và **tiêu thụ hay sinh ra artefact nào**. Từ đó router dựng được một chuỗi skill ngắn, đúng thứ tự và có giải thích cho mỗi việc.

## Gồm những gì

| Thành phần | Làm gì |
|---|---|
| Skill `open-skill-router` | Điểm vào: chọn chuỗi skill, báo chuỗi trong một dòng, chạy bước đầu, ghi lại những gì đã chạy |
| Skill `open-skill-standards` | Checklist "định nghĩa xong" chung và cho từng vai trò |
| Skill `open-skill-intel` | Đưa mỗi câu hỏi tới nguồn tốt nhất: codegraph, Context7, schema, web, ghi chú của bạn, skill graph |
| Skill `open-skill-learn` | Ghi nhớ bài học và thói quen để các lần route sau dùng |
| CLI `open-skill` | `route`, `search`, `scan`, `doctor`, `build`, `validate`, `lint`, `init`, `learn`, `feedback`… |
| Registry | 18 adapter mô tả hơn 190 skill và tool upstream, 28 role pack, 9 hồ sơ model |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/architecture-dark.svg">
  <img src=".github/assets/architecture.svg" alt="Kiến trúc: registry công khai và overlay của tổ chức đi vào scan và index SQLite FTS5; router kết hợp chúng với project của bạn và lớp ~/.open-skill trên máy, rồi coding agent chạy chuỗi skill" width="960">
</picture>

## Bắt đầu nhanh

```bash
# 1. Cài skill (Claude Code) — hoặc: npx skills add VoKhoiNhon/open-skill-standard -g, hoặc xem mục "Dùng với mọi agent" bên dưới
/plugin marketplace add VoKhoiNhon/open-skill-standard
/plugin install open-skill@open-skill-standard

# 2. Khai báo vai trò; lệnh này cũng nạp tri thức khởi đầu (seed) cho vai trò đó
uvx --from git+https://github.com/VoKhoiNhon/open-skill-standard@v0.7.2 open-skill init --role data-engineer=0.7 --role data-analyst=0.3

# 3. Trong agent, ở bất kỳ project nào
/open-skill-router add a pipeline that loads orders into the warehouse
# yêu cầu bằng tiếng Việt cũng được: /open-skill-router thêm pipeline nạp dữ liệu đơn hàng vào warehouse
```

`open-skill doctor` cho biết framework nào đã cài, và in lệnh cài chính thức cho framework còn thiếu.

## Dùng với mọi agent đọc được Agent Skills

Các skill theo định dạng [Agent Skills](https://agentskills.io), nên chạy được trên mọi agent đọc định dạng này. `registry/agents/` mô tả chín agent: mỗi agent nạp skill từ thư mục nào (cho người dùng và cho project), và làm sao biết agent đó đã được cài. Mỗi đường dẫn đều ghi nguồn là tài liệu chính thức của agent, hoặc dòng mã tương ứng trong [vercel-labs/skills](https://github.com/vercel-labs/skills) khi tài liệu không nói.

| Agent | id | Cài vào (người dùng) | Cài vào (project) |
|---|---|---|---|
| Claude Code | `claude-code` | `~/.claude/skills` | `.claude/skills` |
| Codex | `codex` | `~/.agents/skills` | `.agents/skills` |
| Cursor | `cursor` | `~/.cursor/skills` | `.agents/skills` |
| Gemini CLI | `gemini-cli` | `~/.gemini/skills` | `.agents/skills` |
| GitHub Copilot (CLI, coding agent, VS Code) | `github-copilot` | `~/.copilot/skills` | `.github/skills` |
| OpenCode | `opencode` | `~/.config/opencode/skills` | `.opencode/skills` |
| Goose | `goose` | `~/.agents/skills` | `.agents/skills` |
| Windsurf | `windsurf` | `~/.codeium/windsurf/skills` | `.windsurf/skills` |
| Amp | `amp` | `~/.config/agents/skills` | `.agents/skills` |

Mỗi agent còn đọc thêm vài thư mục khác (ví dụ Cursor, Copilot, OpenCode, Goose và Amp đọc cả thư mục của Claude Code); `scan` biết hết các thư mục này và liệt kê mỗi skill một lần, kèm mọi agent nhìn thấy nó.

```bash
open-skill agents                                     # agent nào đã cài, mỗi agent thấy những skill nào
open-skill install open-skill-router --agent codex    # một skill lõi, hoặc đường dẫn tới thư mục skill bất kỳ
open-skill install ./my-skill --agent cursor --project . --symlink
open-skill route "<task>" --agent codex               # chỉ các skill Codex thấy, đúng tên Codex dùng để gọi
open-skill update                                     # cập nhật các skill lõi bạn đã cài theo phiên bản CLI này
open-skill remove open-skill-router --agent codex
```

`install` không bao giờ ghi đè skill mà nó không tự cài. Nó ghi lại mọi thư mục nó tạo, kèm mã băm của từng file, vào `~/.open-skill/installed.json`; `remove` và `update` chỉ đụng tới những thư mục đó, và để nguyên mọi file bạn đã sửa hoặc thêm.

## Router hoạt động thế nào

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/routing-dark.svg">
  <img src=".github/assets/routing.svg" alt="Pipeline routing: yêu cầu, phase và cỡ việc, dải phase, rồi với mỗi phase là lọc ứng viên, chấm điểm và chọn, cuối cùng cắt gọn và ra các bước theo thứ tự" width="960">
</picture>

```text
registry (adapters, roles, models) ─┐
installed skills on this machine ───┼─► in-memory graph + SQLite FTS5 index
your profile, notes, history ───────┘
                       │
open-skill route "<task>" --project . --model <id>
  1. project state: .specify/ or _bmad/ (native framework), artifacts, role signals
  2. role mix → target phase → phase window (role packs can define their own)
  3. per phase: installed candidates, scored by role pack, role weights, text, artifact flow, your history
  4. rules: one build workflow; native framework wins; requirements met; model step limit
  5. output: chain + reasons + your applicable notes + missing skills + model notes
```

1. **Đọc trạng thái project:** có `.specify/` hay `_bmad/` không (framework bản địa), có những artefact nào, tín hiệu nào gợi ý vai trò.
2. **Xác định vai trò, phase đích và các phase cần đi qua.** Role pack có thể tự khai báo chuỗi phase riêng, ví dụ Data Analyst là `build → verify → release`.
3. **Chấm điểm ứng viên đã cài ở từng phase**, dựa trên: role pack, trọng số theo vai trò, độ khớp văn bản, luồng artefact, và lịch sử dùng của bạn.
4. **Áp các luật:**
   - chỉ một quy trình build trong một chuỗi;
   - framework bản địa của project luôn thắng;
   - skill phải đủ điều kiện (ví dụ project đã init);
   - giới hạn số bước theo model đang chạy.
5. **Đầu ra:** chuỗi skill kèm lý do, các ghi chú của bạn liên quan, skill còn thiếu kèm lệnh cài, và ghi chú prompt riêng cho model.

Một route thật (data engineer, project spec-kit chưa cài các skill speckit, Claude Opus 5.5):

```text
1. [plan]   superpowers:writing-plans               — primary for data-engineer; consumes spec
2. [build]  superpowers:subagent-driven-development — primary for data-engineer; consumes plan
3. [verify] data:explore-data                       — primary for data-engineer
4. [review] code-review                             — primary for data-engineer
missing: spec-kit/implement (not installed) → specify init --here --integration claude
missing: codegraph/impact (needs .codegraph in the project) → codegraph init
model note: Deliver what was asked at the intended scope; …
```

## Xem và hỏi ngược skill graph

**Vì sao ra chuỗi này?** `route --explain` cho biết từ khoá nào quyết định phase đích và cỡ việc, vì sao chọn dải phase đó, rồi từng bước kèm điểm và tối đa ba ứng viên xếp sau:

```text
$ open-skill route "add a pipeline that loads orders" --role data-engineer --explain
target build from phase keywords: add, pipeline
size medium: no size keywords, the default
phase window: plan → build → verify → review (medium build task: starts at plan, then verify and review)
1. [plan] superpowers:writing-plans  score=2.5  — phase plan; role prior 2.00 (primary for data-engineer); text 1.00; consumes spec
2. [build] superpowers:subagent-driven-development  score=2.5  — …; consumes plan
   runner-ups: superpowers/test-driven-development 2.0, knowledge-work-data/write-query 0.9, knowledge-work-data/sql-queries 0.7
3. [verify] data:explore-data  score=2.0  — …
   runner-ups: knowledge-work-data/validate-data 2.0 (close call), open-skill/open-skill-standards 2.0, …
```

Khi không có từ khoá phase nào khớp, dòng phase ghi `phase: build (guessed, no signal)` và JSON có `"phase_from": "guessed"`. Agent đã đọc cuộc hội thoại nên tự truyền `--phase` (và `--size`); dò từ khoá chỉ là phương án dự phòng.

**Sao không chọn skill kia?** `--why-not` nhận id hoặc tên gọi của skill và nêu lý do: chưa cài (kèm lệnh cài), sai phase hoặc sai cỡ việc, project chưa đủ điều kiện, xung đột với skill đã chọn, điểm dưới ngưỡng hoặc thua skill thắng (hiện cả hai điểm), bị cắt vì giới hạn số bước của model, hoặc việc đủ nhỏ để làm thẳng.

```text
$ open-skill route "add a pipeline that loads orders" --role data-engineer --why-not superpowers:executing-plans
superpowers/executing-plans is not in the chain for: add a pipeline that loads orders
  - [build] score 0.375 lost to superpowers/subagent-driven-development (2.5)
$ open-skill route "add a pipeline that loads orders" --role data-engineer --why-not superpowers/brainstorming
superpowers/brainstorming is not in the chain for: add a pipeline that loads orders
  - acts in discover, specify; this task's phase window is plan, build, verify, review
```

**Có những gì?** `search` lọc theo `--role`, `--phase`, `--source` và `--installed`; bỏ trống câu tìm thì liệt kê mọi skill qua được bộ lọc:

```text
$ open-skill search --role data-engineer --phase verify --installed
      -  knowledge-work-data/explore-data
      -  knowledge-work-data/validate-data
      -  superpowers/test-driven-development
      …
```

**Toàn bộ graph.** `open-skill graph --format html --out graph.html` ghi ra một trang HTML duy nhất, tự chứa, không cần mạng: skill theo phase; artefact, điều kiện, xung đột và vai trò khuyên dùng của từng skill; bảng artefact và danh sách vai trò; lọc theo vai trò, phase, nguồn, đã cài hay chưa, và ô tìm kiếm. Dùng được bằng bàn phím (`/` để tìm, `Esc` để xoá) và theo giao diện sáng/tối của máy. `--format json` và `--format mermaid` xuất cùng graph cho công cụ khác.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/graph-viewer-dark.png">
  <img src=".github/assets/graph-viewer.png" alt="Trang skill graph từ open-skill graph --format html: skill nhóm theo phase, lọc theo vai trò, phase, nguồn và trạng thái cài đặt" width="960">
</picture>

## Nhiều session song song

Nhiều session agent có thể cùng làm trên một project và dùng chung một code graph [Graphify](https://github.com/Graphify-Labs/graphify). Mỗi session khai báo các đường dẫn mình phụ trách. Sau khi sửa, `session update` cập nhật graph (Graphify tự khoá và ghi lại, khoảng 2.4 s trên repo này) rồi liệt kê các file cách những gì đã đổi từ lúc session bắt đầu, đã commit hay chưa, trong vòng hai bước theo lời gọi, tham chiếu hoặc import. Nếu một file trong đó thuộc phạm vi của session khác thì lệnh cảnh báo. Lệnh không bao giờ chặn và không bao giờ báo lỗi vì đụng độ.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/sessions-dark.svg">
  <img src=".github/assets/sessions.svg" alt="Nhiều session song song: các session khai báo phạm vi, dùng chung một working tree và một graph Graphify; session update cập nhật graph, lấy các file đổi từ lúc session bắt đầu, tách riêng việc của session khác, duyệt ngược hai bước theo lời gọi, tham chiếu và import, rồi báo đụng độ, việc của session khác và các file bị ảnh hưởng" width="960">
</picture>

```bash
uv tool install graphifyy && graphify extract . --code-only    # once per project
open-skill session start --scope "cli/open_skill/route.py" --task "speed up fit"
open-skill session start --scope "tests/**" --task "add fixtures for route tests"
open-skill session update --session <id>          # after an edit, from the session that made it
open-skill session list                           # --prune drops sessions idle for more than 6 hours
open-skill session end <id>
```

```text
$ open-skill session update --session a1b2c3
graph: 2204 nodes, 3566 edges (refreshed)
changed: cli/open_skill/route.py
affected: 14 files
  cli/open_skill/cli.py
  …
⚠ tests/test_route.py is in session b4c5d6 ("add fixtures for route tests"), reached from cli/open_skill/route.py
```

Graphify nối `from pkg import mod` tới package chứ không tới `mod.py`, và không nhận `mod.fn()` là một lời gọi hàm; `session update` tự nối các import qua package, nên test có import module vẫn được tìm thấy. Khi có `--session`, file đã đổi chỉ nằm trong phạm vi của session khác được tính là việc của session đó (liệt kê với `·`), vì các session dùng chung một working tree. Với câu hỏi ở mức lời gọi hàm (ai gọi, ảnh hưởng) thì vẫn dùng codegraph. Bản ghi session nằm trong `.open-skill/sessions/` của project, thư mục này tự bỏ qua trong git. `--json` trả danh sách file đổi, bị ảnh hưởng và đụng độ cho agent dùng tiếp.

## 28 vai trò

| Nhóm | Vai trò |
|---|---|
| Kỹ thuật | frontend, backend, fullstack, mobile, embedded, game |
| Chất lượng & vận hành | QA, DevOps, SRE, cloud, security, DBA, system admin |
| Dữ liệu & AI | data engineer, analytics engineer, data analyst, data scientist, ML engineer, AI engineer, data/AI platform engineer |
| Kiến trúc & lãnh đạo | software architect, tech lead, engineering manager |
| Sản phẩm & delivery | product manager, business analyst, UX designer, technical writer, scrum master |

Mỗi role pack ghi rủi ro đặc thù của vai trò, các nguyên tắc (dùng làm constitution cho spec-kit), tín hiệu nhận diện project, và skill primary/alternative cho từng phase.

Cùng một kiểu yêu cầu nhưng khác vai trò thì ra chuỗi khác:

<img src=".github/assets/route-backend.svg" alt="Terminal: open-skill route --explain cho backend developer thêm endpoint xuất CSV, lập kế hoạch và build bằng các skill backend" width="790">
<img src=".github/assets/route-sre.svg" alt="Terminal: open-skill route --explain cho site reliability engineer khi request checkout bị timeout, bắt đầu bằng debug" width="790">

## Các framework được tích hợp

Adapter mô tả skill của từng nguồn dưới dạng metadata và trỏ tới trình cài đặt chính thức; repo không chép nội dung của nguồn nào.

| Nguồn | Vai trò trong chuỗi | Giấy phép |
|---|---|---|
| [superpowers](https://github.com/obra/superpowers) | Kỷ luật thực thi: duyệt thiết kế, kế hoạch, TDD, debug, xác minh | MIT |
| [BMad Method](https://github.com/bmad-code-org/BMAD-METHOD) | Bạn đồng hành tư duy, persona, artefact lập kế hoạch, build vừa cỡ (cần `bmad setup`) | MIT, nhãn hiệu |
| [spec-kit](https://github.com/github/spec-kit) | Spec bền vững → plan → tasks → implement → converge (cần `specify init`) | MIT |
| [codegraph](https://github.com/colbymchenry/codegraph) | Đồ thị tri thức về code: đường gọi hàm, tác động, test bị ảnh hưởng | MIT |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Code graph dùng chung cho các session song song; cập nhật bằng `open-skill session update` | Apache-2.0 |
| [Anthropic skills](https://github.com/anthropics/skills) | Tài liệu, viết skill, MCP server, kiểm thử web, thiết kế frontend | theo từng skill |
| [Knowledge-work plugins](https://github.com/anthropics/knowledge-work-plugins) | Dữ liệu, kỹ thuật, quản lý sản phẩm, thiết kế | Apache-2.0 |
| [Context7](https://github.com/upstash/context7) | Tài liệu thư viện mới nhất | MIT |
| [ponytail](https://github.com/DietrichGebert/ponytail) | Giải pháp tối giản và review chống over-engineering | MIT |
| [taste-skill](https://github.com/leonxlnx/taste-skill) | Chất lượng thị giác của frontend | MIT |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Vòng đời kỹ thuật: spec, chia task, lát mỏng, observability, hardening, migration, launch | MIT |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | Quy tắc React, Next.js và React Native, review UI và văn phong, deploy Vercel và tối ưu chi phí | MIT |
| Skill có sẵn của Claude Code | code-review, security-review, run, claude-api, schedule… | — |

Các framework nối với nhau thế nào: skill ở mỗi phase tạo ra artefact mà phase sau dùng tới. `open-skill doctor` cho biết nguồn nào đã cài và lệnh cài cho phần còn lại:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/lifecycle-dark.svg">
  <img src=".github/assets/lifecycle.svg" alt="Graph vòng đời: 10 phase và 19 artefact của taxonomy, cùng các artefact mà skill ở mỗi phase tạo ra và dùng tới" width="960">
</picture>

<img src=".github/assets/doctor.svg" alt="Terminal: open-skill doctor liệt kê từng nguồn được tích hợp, số skill đã cài và đã mô tả, và lệnh cài cho những gì còn thiếu" width="790">

## Thích ứng theo model

Cách prompt tốt thay đổi theo từng thế hệ model; chỉ dẫn từng giúp ích cho model cũ có thể gây hại cho model mới. Vì vậy:

- **Skill viết trung lập với model.** Chỉ dẫn riêng từng model nằm trong `registry/models/`: effort theo độ lớn việc, độ dài chuỗi, ghi chú prompt, các mẫu cần tránh. Mỗi mục có nguồn từ hướng dẫn prompt của Anthropic.
- **Model mới không làm hỏng gì.** Model chưa có hồ sơ sẽ rơi về hồ sơ cùng họ model, hoặc về `generic`.
- **Tự phát hiện model mới.** Workflow chạy hằng tuần tự mở issue khi Anthropic ra model chưa có hồ sơ.
- **`open-skill lint`** chặn các mẫu không còn phù hợp: yêu cầu viết lại suy luận vào câu trả lời, lệnh "double-check" thừa, model ID viết cứng.

## Đo lường

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/benchmark-dark.svg">
  <img src=".github/assets/benchmark.svg" alt="Benchmark routing trên 52 yêu cầu holdout: chỉ khớp description 17%, skill ngẫu nhiên trong các phase của router 50%, router không phát hiện phase 33%, không có role prior 54%, router Open Skill 67%, kèm khoảng tin cậy Wilson 95%" width="960">
</picture>

Trên 52 yêu cầu holdout, router đạt 67% [54–78%] số ca, so với 17% [9–30%] khi chỉ chọn một skill có description khớp nhất (BM25 trên cùng index): thắng 29, thua 3, kiểm định McNemar chính xác p = 3×10⁻⁶. Bỏ phát hiện phase thì còn 33%, bỏ role prior còn 54%; chọn skill ngẫu nhiên trong chính các phase của router đạt 50%. Cả 199 ca đã tinh chỉnh đều đạt, đúng như CI yêu cầu. Một lần route mất vài mili giây và có 1.179 test bảo vệ. Nhãn do maintainer tự gán, 52 ca cho khoảng tin cậy rộng, và đây là đo routing chứ không đo phần việc sau đó. `uv run python -m open_skill.benchmark` tái lập mọi con số (`--json` để lấy dạng máy đọc); `scripts/render_assets.py` vẽ lại biểu đồ từ đó và CI kiểm tra biểu đồ luôn cập nhật.

- `open-skill eval routing` chạy các ca routing đã gán nhãn (mọi vai trò, framework, model) và báo tỉ lệ đạt theo vai trò, rồi điểm trên bộ ca giữ riêng (holdout) mà router chưa từng được chỉnh theo (yêu cầu diễn đạt lại, viết lộn xộn, tiếng Anh và tiếng Việt có dấu lẫn không dấu). CI đòi mọi ca đã chỉnh phải đạt và holdout không tụt dưới một ngưỡng sàn.
- `open-skill eval triggers` đo xem description của mỗi core skill có bắt đúng các yêu cầu cần bắt và bỏ qua các câu "suýt khớp" hay không, với khoảng 30 câu gán nhãn cho mỗi skill; các câu có `holdout: true` không bao giờ được dùng để tinh chỉnh. Mặc định dùng proxy lexical tất định (nhanh, chạy trong CI với ngưỡng chống tụt hạng) và chỉ liệt kê câu bị bỏ sót hoặc kích hoạt nhầm trong tập tinh chỉnh; `--agent claude --runs 3` chạy từng câu qua Claude Code, tính là kích hoạt khi skill được gọi ở ít nhất nửa số lần, và báo precision/recall trên tập tinh chỉnh và tập holdout. `--suggest` liệt kê thêm, cho mỗi skill, các từ và cụm từ chung của những câu tinh chỉnh bị bỏ sót mà description còn thiếu, và các từ trong description gây kích hoạt nhầm: gợi ý về khái niệm còn thiếu, không phải từ để chép nguyên văn.

## Sức khoẻ của skill

`open-skill lint` kiểm tra skill theo [đặc tả Agent Skills](https://agentskills.io/specification) (luật đặt tên và khớp thư mục, giới hạn các trường, file được tham chiếu) và theo hướng dẫn prompt hiện hành; plugin manifest cũng được kiểm tra. Chỉ lỗi mới làm lệnh thất bại; `--strict` coi cả cảnh báo là lỗi, `--format json` để dùng cho công cụ khác. `open-skill lint --installed` báo cáo sức khoẻ của mọi skill đã cài, nhóm theo nguồn.

## Kiểm tra bảo mật

Skill chạy với quyền của agent, nên hãy xem xét một skill trước khi tin nó. `open-skill audit` hỗ trợ việc đó: lệnh đọc mọi file trong thư mục skill (SKILL.md, references, scripts, assets) và báo những dòng cần người xem lại. Lệnh không bao giờ chạy, sửa, hay đi theo liên kết ra khỏi các file được kiểm tra.

```bash
open-skill audit ./downloaded-skill        # một thư mục, trước khi cài
open-skill audit --installed               # mọi skill đã cài, nhóm theo nguồn
open-skill audit --installed --format json # cho công cụ khác
```

Lệnh đánh dấu câu chữ tìm cách ghi đè chỉ dẫn của người dùng hay của hệ thống, giấu hành động khỏi người dùng, bỏ qua hoặc giả mạo sự đồng ý, mạo danh hệ thống hay quản trị viên, hoặc nhắm tới khoá SSH, thông tin đăng nhập cloud, file `.env`, dữ liệu trình duyệt và kho mật khẩu; ký tự Unicode vô hình và chú thích HTML nói với agent; quyền shell không giới hạn trong `allowed-tools` và lệnh chạy ngay khi skill được nạp; liên kết trỏ ra ngoài thư mục skill và file thực thi đi kèm. Mỗi phát hiện ghi file, dòng, đoạn trích đã được escape, lý do, và nguồn công khai của luật (OWASP Top 10 cho ứng dụng LLM, MITRE ATT&CK, tài liệu của Anthropic và Claude Code). Lệnh trả mã 1 khi có phát hiện mức high; `--strict` coi cả medium và low là lỗi. `open-skill doctor` hiện một dòng tóm tắt.

Đây là công cụ rà soát theo heuristic, không phải lời bảo đảm. Một phát hiện có thể vô hại trong ngữ cảnh của nó, và báo cáo sạch chỉ có nghĩa là không luật nào khớp: kẻ tấn công cẩn thận có thể viết theo cách các luật không bắt được. Vẫn hãy tự đọc skill từ nguồn lạ, và ưu tiên skill do bạn hoặc tổ chức của bạn duy trì.

<img src=".github/assets/audit.svg" alt="Terminal: open-skill audit ./downloaded-skill báo các phát hiện theo mức độ, kèm file và dòng" width="790">

## Hiểu bạn, ngay trên máy bạn

- **Dữ liệu cá nhân nằm trong `~/.open-skill/`:** hồ sơ, ghi chú (mỗi file một ý) và lịch sử dùng.
- **Router dùng chúng thế nào:** mỗi lần route, router gắn kèm các ghi chú liên quan, và lịch sử dùng điều chỉnh thứ hạng skill (giảm một nửa sau mỗi 90 ngày).
- **Quyền riêng tư:**
  - `learn` từ chối nội dung giống secret hoặc dữ liệu cá nhân.
  - `forget` và `export` chỉ cần một lệnh.
  - Không bao giờ có dữ liệu nào trong thư mục này được public.
- **Dùng lại memory của Claude:** `open-skill scan --memory` import memory của Claude Code ở chế độ chỉ đọc.

### Cập nhật không bao giờ đụng vào ghi chú của bạn

Khi kéo bản mới (cập nhật plugin, `npx skills update`, bản `uvx` mới), chỉ có skill và registry được thay; dữ liệu của bạn nằm ở `~/.open-skill/`, ngoài mọi thư mục skill. Sau khi kéo bản mới, chạy:

```bash
open-skill upgrade --dry-run   # xem trước những gì sẽ đổi
open-skill upgrade             # backup, nâng schema dữ liệu, đồng bộ tri thức khởi đầu
```

- Seed bạn chưa sửa sẽ theo nội dung mới; seed bạn đã sửa được giữ nguyên, còn nội dung mới nằm chờ trong `seed-updates/` để bạn dùng `open-skill seeds diff | accept | keep`.
- Seed bạn đã xoá không bao giờ bị tạo lại; seed upstream bỏ đi vẫn được giữ và chỉ báo một lần.
- CLI cũ từ chối ghi vào dữ liệu do bản mới tạo. `open-skill upgrade --rollback`, `backup` và `restore` giúp hoàn tác mọi thứ.

**Skill nội bộ của công ty** được đặt trong một **overlay L1**: một repo riêng có cùng cấu trúc, nạp qua `--overlay`. Bạn không cần fork repo này và cũng không phải đưa gì nội bộ lên public.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/safety-dark.svg">
  <img src=".github/assets/safety.svg" alt="An toàn dữ liệu: khi cập nhật, open-skill sao lưu, migrate và đồng bộ ghi chú khởi đầu; seed chưa sửa được cập nhật, seed đã sửa được giữ lại kèm đề xuất, seed đã bỏ không bao giờ tạo lại, ghi chú của bạn không bao giờ bị đụng tới" width="960">
</picture>

<img src=".github/assets/upgrade.svg" alt="Terminal: open-skill upgrade --dry-run cho thấy lần cập nhật sẽ làm gì với ghi chú từ bản cũ" width="790">

## CLI

```text
open-skill route "<task>" [--project .] [--agent a] [--role r] [--size s] [--phase p] [--model m] [--explain | --why-not <skill>]
open-skill search ["<need>"] [--role r] [--phase p] [--source s] [--installed] [--agent a]
open-skill doctor                   open-skill scan [--agent a] [--memory]
open-skill agents [--project .]     open-skill install <skill|folder> --agent a [--project .] [--symlink] [--dry-run]
open-skill remove <skill> --agent a [--project .] [--dry-run]    open-skill update [--agent a] [--dry-run]
open-skill init --role r[=w]        open-skill learn "<fact>" --applies-to skill:<id>,role:<id>
open-skill feedback <route_id> --ran a,b --outcome ok|fail       open-skill forget <id>
open-skill validate | lint [paths] | build [--check] | graph [--format mermaid|json|html] [--out file]
open-skill audit [paths] [--installed] [--format json] [--strict]
open-skill adapter draft|check --source <name> --from <upstream checkout>
open-skill session start --scope <glob> --task "..." | list [--prune] | end <id> | update [--session <id>] [--json]
```

Mã thoát: 0 thành công, 1 một kiểm tra thất bại (lint có lỗi, audit có phát hiện mức high, build cũ, adapter lệch upstream, không có gì để gỡ), 2 đầu vào sai (vai trò, phase, agent hoặc đường dẫn không tồn tại), 3 dữ liệu của bạn do một open-skill mới hơn ghi.

### Đầu ra JSON

Các đầu ra này dành cho công cụ khác; các khoá liệt kê luôn có mặt (có thể thêm khoá, không bao giờ bỏ khoá trong một bản minor).

| Lệnh | Dạng | Khoá |
|---|---|---|
| `open-skill route` | object | `route_id`, `task`, `agent`, `role`, `size`, `target_phase`, `phase_from`, `project`, `chain`, `advice`, `knowledge`, `missing`, `model` |
| `open-skill scan --json` | list of objects | `id`, `invoke`, `path`, `description`, `inferred`, `agent`, `agents` |
| `open-skill agents --json` | list of objects | `id`, `name`, `detected`, `skills`, `docs`, `install_to`, `reads` |
| `open-skill status --json` | object | `open_skill`, `registry`, `home`, `data_schema`, `cli_schema`, `pending_migrations`, `roles`, `notes`, `seed_updates_to_review`, `backups` |
| `open-skill lint --format json` | list of objects | `path`, `severity`, `rule`, `message`, `source` |
| `open-skill lint --installed --format json` | object per source | `skills`, `errors`, `warnings`, `worst` |
| `open-skill audit --format json` | object | `disclaimer`, `summary`, `groups` |
| `open-skill graph --format json` | object | `version`, `nodes`, `edges` |
| `open-skill eval routing --format json` | object | `cases`, `passed`, `pass_rate`, `by_role`, `results` |
| `open-skill eval triggers --format json` | object per skill | `train`, `validation` |

## Đóng góp

Bạn có thể thêm adapter, role pack hoặc hồ sơ model; xem [CONTRIBUTING.md](CONTRIBUTING.md). Mỗi thay đổi đều chạy: unit test, routing eval cho mọi vai trò, validate schema, lint skill, kiểm tra file sinh tự động, và privacy guard.

Chính repo này cũng được phát triển theo hướng spec-driven: xem `.specify/memory/constitution.md` và `specs/`.

## Lời cảm ơn

Dự án dựa trên ý tưởng và công sức của superpowers (Jesse Vincent), BMad Method (BMad Code, LLC), spec-kit (GitHub), codegraph (Colby McHenry), Agent Skills và plugin của Anthropic, Context7 (Upstash), ponytail, taste-skill, agent-skills của Addy Osmani và agent-skills của Vercel. Xem [NOTICE](NOTICE).

## Giấy phép

MIT © Võ Khôi Nhơn. Phát triển cùng Claude với vai trò đồng tác giả.
