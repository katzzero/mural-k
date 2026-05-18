# Mural-K

A self-hosted Kanban board built with Flask, SQLite, and vanilla JavaScript, running in a lightweight Alpine Docker container.

## Features

- Drag-and-drop cards between columns
- Live card preview while dragging
- Checklists (todos) inside cards
- Click checkboxes on cards to mark items done
- Trash bin: drag cards to trash, restore them later
- Column width modes: Fit (auto), Absolute (pixels), Proportional (percentage)
- Customizable column colors (background + accent)
- Customizable color palette for cards
- Editable mural title
- Border radius settings for cards and columns
- Data persistence via SQLite
- Lightweight Alpine-based Docker image (multi-architecture: amd64 + arm64)

## Quick Start

### Using Docker

```bash
docker run -d -p 8080:5000 -v mural-k-data:/data --name mural-k katzzero/mural-k
```

Open http://localhost:8080

### Using Docker Compose

```bash
docker compose up -d
```

## Configuration

Mural settings (name, background color, border radius, column width mode, palette colors) are stored in browser localStorage and persist across sessions.

Column settings (background color, accent color, proportional width) are stored per column in the SQLite database and persist across restarts.

## Data Persistence

The SQLite database is stored at `/data/k.sqlite` inside the container. Use a Docker volume to persist it:

```bash
docker run -d -p 8080:5000 -v mural-k-data:/data --name mural-k katzzero/mural-k
```

## Build from source

```bash
git clone https://github.com/katzzero/mural-k.git
cd mural-k
docker build -t mural-k .
docker run -d -p 8080:5000 -v mural-k-data:/data --name mural-k mural-k
```

## Architecture

- **Backend**: Flask (Python) + SQLite
- **Frontend**: Vanilla JavaScript, no frameworks
- **Container**: Alpine Linux (approx. 90MB)
- **Platforms**: linux/amd64, linux/arm64

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /api/columns | List all columns |
| POST | /api/columns | Create a column |
| PUT | /api/columns/:id | Update a column |
| DELETE | /api/columns/:id | Delete a column |
| GET | /api/columns/:id/cards | List cards in a column |
| POST | /api/cards | Create a card |
| PUT | /api/cards/:id | Update a card |
| DELETE | /api/cards/:id | Move card to trash |
| GET | /api/cards/:id/todos | List todos on a card |
| POST | /api/todos | Create a todo |
| PUT | /api/todos/:id | Update a todo |
| DELETE | /api/todos/:id | Delete a todo |
| GET | /api/cards/trash | List trashed cards |
| PUT | /api/cards/:id/restore | Restore a card from trash |

## License

MIT
