import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import App from "./App";

const mockRecords = [
  { id: 1, filename: "audio1.mp3", transcript: "Hello world", created_on: "2026-01-01T10:00:00Z" },
  { id: 2, filename: "audio2.mp3", transcript: "Foo bar", created_on: "2026-01-02T12:00:00Z" },
];

beforeEach(() => {
  jest.clearAllMocks();
  global.fetch = jest.fn();
  jest.spyOn(window, "alert").mockImplementation(() => {});
});

function mockFetchRecords(records = mockRecords) {
  global.fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => records,
  });
}

async function renderApp() {
  mockFetchRecords();
  render(<App />);
  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
}

async function renderAppEmpty() {
  global.fetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
  render(<App />);
  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
}

// ─── Rendering ────────────────────────────────────────────────────────────────

describe("Initial render", () => {
  it("renders app", async () => {
    await renderApp();
    expect(screen.getByPlaceholderText(/search by filename/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/upload audio/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("audio1.mp3")).toBeInTheDocument();
      expect(screen.getByText("audio2.mp3")).toBeInTheDocument();
    });

  });
});

// ─── Search ───────────────────────────────────────────────────────────────────

describe("Search", () => {
  it("calls the search endpoint when Search", async () => {
    await renderApp();
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => [mockRecords[0]] });

    userEvent.type(screen.getByPlaceholderText(/search by filename/i), "audio1{Enter}");

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/search?filename=audio1")
      )
    );
  });

  it("updates the table with search results", async () => {
    await renderApp();
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => [mockRecords[0]] });

    userEvent.type(screen.getByPlaceholderText(/search by filename/i), "audio1");
    userEvent.click(screen.getByRole("button", { name: /search/i }));

    await waitFor(() => expect(screen.queryByText("audio2.mp3")).not.toBeInTheDocument());
    expect(screen.getByText("audio1.mp3")).toBeInTheDocument();
  });
});

// ─── Upload ───────────────────────────────────────────────────────────────────

describe("File upload", () => {
  it("shows success status after a successful upload", async () => {
    await renderAppEmpty();

    const updatedRecords = [
      ...mockRecords,
      { id: 3, filename: "new.mp3", transcript: "New one", created_on: null },
    ];

    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ results: [{ filename: "new.mp3" }], errors: [] }),
    });
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => updatedRecords });

    await userEvent.upload(
      document.querySelector("#file-input"),
      new File(["audio"], "new.mp3", { type: "audio/mpeg" })
    );

    await waitFor(() =>
      expect(window.alert).toHaveBeenCalledWith(expect.stringMatching(/new\.mp3/i))
    );
    await waitFor(() =>
      expect(screen.getByText("new.mp3")).toBeInTheDocument()
    );
  });

  it("shows error status after a failed upload", async () => {
    await renderAppEmpty();
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ results: [], errors: [{ filename: "fail.mp3", error: "Server error" }] }),
    });

    await userEvent.upload(
      document.querySelector("#file-input"),
      new File(["audio"], "fail.mp3", { type: "audio/mpeg" })
    );

    await waitFor(() =>
      expect(window.alert).toHaveBeenCalledWith(expect.stringMatching(/fail\.mp3/i))
    );
  });
});