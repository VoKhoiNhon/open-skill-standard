# Open Skill Standard (tiếng Việt)

**Một router, một skill graph, 28 vai trò IT.** Đây là một chuẩn mở, không phụ thuộc agent, để chọn đúng Agent Skill cho từng việc. Repo kèm bản triển khai tham chiếu, nối các bộ superpowers, BMad Method, spec-kit, codegraph, skill của Anthropic và nhiều nguồn khác mà không sao chép nội dung của bộ nào.

[English](README.md) · [Đặc tả](spec/SPEC.md) · [Đóng góp](CONTRIBUTING.md)

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
| Registry | 16 adapter mô tả hơn 190 skill và tool upstream, 28 role pack, 9 hồ sơ model |

## Bắt đầu nhanh

```bash
# 1. Cài skill (Claude Code) — hoặc: npx skills add VoKhoiNhon/open-skill-standard -g, hoặc xem mục "Dùng với mọi agent" bên dưới
/plugin marketplace add VoKhoiNhon/open-skill-standard
/plugin install open-skill@open-skill-standard

# 2. Khai báo vai trò; lệnh này cũng nạp tri thức khởi đầu (seed) cho vai trò đó
uvx --from git+https://github.com/VoKhoiNhon/open-skill-standard@v0.5.0 open-skill init --role data-engineer=0.7 --role data-analyst=0.3

# 3. Trong agent, ở bất kỳ project nào
/open-skill-router thêm pipeline nạp dữ liệu đơn hàng vào warehouse
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
open-skill route "<việc cần làm>" --agent codex       # chỉ các skill Codex thấy, đúng tên Codex dùng để gọi
open-skill update                                     # cập nhật các skill lõi bạn đã cài theo phiên bản CLI này
open-skill remove open-skill-router --agent codex
```

`install` không bao giờ ghi đè skill mà nó không tự cài. Nó ghi lại mọi thư mục nó tạo, kèm mã băm của từng file, vào `~/.open-skill/installed.json`; `remove` và `update` chỉ đụng tới những thư mục đó, và để nguyên mọi file bạn đã sửa hoặc thêm.

## Router hoạt động thế nào

1. **Đọc trạng thái project:** có `.specify/` hay `_bmad/` không (framework bản địa), có những artefact nào, tín hiệu nào gợi ý vai trò.
2. **Xác định vai trò, phase đích và các phase cần đi qua.** Role pack có thể tự khai báo chuỗi phase riêng, ví dụ Data Analyst là `build → verify → release`.
3. **Chấm điểm ứng viên đã cài ở từng phase**, dựa trên: role pack, trọng số theo vai trò, độ khớp văn bản, luồng artefact, và lịch sử dùng của bạn.
4. **Áp các luật:**
   - chỉ một quy trình build trong một chuỗi;
   - framework bản địa của project luôn thắng;
   - skill phải đủ điều kiện (ví dụ project đã init);
   - giới hạn số bước theo model đang chạy.
5. **Đầu ra:** chuỗi skill kèm lý do, các ghi chú của bạn liên quan, skill còn thiếu kèm lệnh cài, và ghi chú prompt riêng cho model.

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
```

**Sao không chọn skill kia?** `--why-not` nhận id hoặc tên gọi của skill và nêu lý do: chưa cài (kèm lệnh cài), sai phase hoặc sai cỡ việc, project chưa đủ điều kiện, xung đột với skill đã chọn, điểm dưới ngưỡng hoặc thua skill thắng (hiện cả hai điểm), bị cắt vì giới hạn số bước của model, hoặc việc đủ nhỏ để làm thẳng.

```text
$ open-skill route "add a pipeline that loads orders" --role data-engineer --why-not superpowers:executing-plans
superpowers/executing-plans is not in the chain for: add a pipeline that loads orders
  - [build] score 0.375 lost to superpowers/subagent-driven-development (2.5)
```

**Có những gì?** `search` lọc theo `--role`, `--phase`, `--source` và `--installed`; bỏ trống câu tìm thì liệt kê mọi skill qua được bộ lọc:

```text
$ open-skill search --role data-engineer --phase verify --installed
      -  knowledge-work-data/explore-data
      -  knowledge-work-data/validate-data
      …
```

**Toàn bộ graph.** `open-skill graph --format html --out graph.html` ghi ra một trang HTML duy nhất, tự chứa, không cần mạng: skill theo phase; artefact, điều kiện, xung đột và vai trò khuyên dùng của từng skill; bảng artefact và danh sách vai trò; lọc theo vai trò, phase, nguồn, đã cài hay chưa, và ô tìm kiếm. Dùng được bằng bàn phím (`/` để tìm, `Esc` để xoá) và theo giao diện sáng/tối của máy. `--format json` và `--format mermaid` xuất cùng graph cho công cụ khác.

## 28 vai trò

| Nhóm | Vai trò |
|---|---|
| Kỹ thuật | frontend, backend, fullstack, mobile, embedded, game |
| Chất lượng & vận hành | QA, DevOps, SRE, cloud, security, DBA, system admin |
| Dữ liệu & AI | data engineer, analytics engineer, data analyst, data scientist, ML engineer, AI engineer, data/AI platform engineer |
| Kiến trúc & lãnh đạo | software architect, tech lead, engineering manager |
| Sản phẩm & delivery | product manager, business analyst, UX designer, technical writer, scrum master |

Mỗi role pack ghi rủi ro đặc thù của vai trò, các nguyên tắc (dùng làm constitution cho spec-kit), tín hiệu nhận diện project, và skill primary/alternative cho từng phase.

## Thích ứng theo model

Cách prompt tốt thay đổi theo từng thế hệ model; chỉ dẫn từng giúp ích cho model cũ có thể gây hại cho model mới. Vì vậy:

- **Skill viết trung lập với model.** Chỉ dẫn riêng từng model nằm trong `registry/models/`: effort theo độ lớn việc, độ dài chuỗi, ghi chú prompt, các mẫu cần tránh. Mỗi mục có nguồn từ hướng dẫn prompt của Anthropic.
- **Model mới không làm hỏng gì.** Model chưa có hồ sơ sẽ rơi về hồ sơ cùng họ model, hoặc về `generic`.
- **Tự phát hiện model mới.** Workflow chạy hằng tuần tự mở issue khi Anthropic ra model chưa có hồ sơ.
- **`open-skill lint`** chặn các mẫu không còn phù hợp: yêu cầu viết lại suy luận vào câu trả lời, lệnh "double-check" thừa, model ID viết cứng.

## Đo lường

- `open-skill eval routing` chạy các ca routing đã gán nhãn (mọi vai trò, framework, model) và báo tỉ lệ đạt theo vai trò.
- `open-skill eval triggers` đo xem description của mỗi core skill có bắt đúng các yêu cầu cần bắt và bỏ qua các câu "suýt khớp" hay không, với khoảng 30 câu gán nhãn cho mỗi skill; các câu có `holdout: true` không bao giờ được dùng để tinh chỉnh. Mặc định dùng proxy lexical tất định (nhanh, chạy trong CI với ngưỡng chống tụt hạng) và chỉ liệt kê câu bị bỏ sót hoặc kích hoạt nhầm trong tập tinh chỉnh; `--agent claude --runs 3` chạy từng câu qua Claude Code, tính là kích hoạt khi skill được gọi ở ít nhất nửa số lần, và báo precision/recall trên tập tinh chỉnh và tập holdout. `--suggest` liệt kê thêm, cho mỗi skill, các từ và cụm từ chung của những câu tinh chỉnh bị bỏ sót mà description còn thiếu, và các từ trong description gây kích hoạt nhầm: gợi ý về khái niệm còn thiếu, không phải từ để chép nguyên văn.

## Sức khoẻ của skill

`open-skill lint` kiểm tra skill theo [đặc tả Agent Skills](https://agentskills.io/specification) (luật đặt tên và khớp thư mục, giới hạn các trường, file được tham chiếu) và theo hướng dẫn prompt hiện hành; plugin manifest cũng được kiểm tra. Chỉ lỗi mới làm lệnh thất bại; `--strict` coi cả cảnh báo là lỗi, `--format json` để dùng cho công cụ khác. `open-skill lint --installed` báo cáo sức khoẻ của mọi skill đã cài, nhóm theo nguồn.

## Kiểm tra bảo mật

Skill chạy với quyền của agent, nên hãy xem xét một skill trước khi tin nó. `open-skill audit` hỗ trợ việc đó: lệnh đọc mọi file trong thư mục skill (SKILL.md, references, scripts, assets) và báo những dòng cần người xem lại. Lệnh không bao giờ chạy, sửa, hay đi theo liên kết ra khỏi các file được kiểm tra.

```bash
open-skill audit ./skill-vua-tai            # một thư mục, trước khi cài
open-skill audit --installed               # mọi skill đã cài, nhóm theo nguồn
open-skill audit --installed --format json # cho công cụ khác
```

Lệnh đánh dấu câu chữ tìm cách ghi đè chỉ dẫn của người dùng hay của hệ thống, giấu hành động khỏi người dùng, bỏ qua hoặc giả mạo sự đồng ý, mạo danh hệ thống hay quản trị viên, hoặc nhắm tới khoá SSH, thông tin đăng nhập cloud, file `.env`, dữ liệu trình duyệt và kho mật khẩu; ký tự Unicode vô hình và chú thích HTML nói với agent; quyền shell không giới hạn trong `allowed-tools` và lệnh chạy ngay khi skill được nạp; liên kết trỏ ra ngoài thư mục skill và file thực thi đi kèm. Mỗi phát hiện ghi file, dòng, đoạn trích đã được escape, lý do, và nguồn công khai của luật (OWASP Top 10 cho ứng dụng LLM, MITRE ATT&CK, tài liệu của Anthropic và Claude Code). Lệnh trả mã 1 khi có phát hiện mức high; `--strict` coi cả medium và low là lỗi. `open-skill doctor` hiện một dòng tóm tắt.

Đây là công cụ rà soát theo heuristic, không phải lời bảo đảm. Một phát hiện có thể vô hại trong ngữ cảnh của nó, và báo cáo sạch chỉ có nghĩa là không luật nào khớp: kẻ tấn công cẩn thận có thể viết theo cách các luật không bắt được. Vẫn hãy tự đọc skill từ nguồn lạ, và ưu tiên skill do bạn hoặc tổ chức của bạn duy trì.

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

## Đóng góp

Bạn có thể thêm adapter, role pack hoặc hồ sơ model; xem [CONTRIBUTING.md](CONTRIBUTING.md). Mỗi thay đổi đều chạy: unit test, routing eval cho mọi vai trò, validate schema, lint skill, kiểm tra file sinh tự động, và privacy guard.

## Giấy phép

MIT © Võ Khôi Nhơn. Phát triển cùng Claude với vai trò đồng tác giả.
