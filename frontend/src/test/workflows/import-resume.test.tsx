/**
 * Workflow 1: Import resume → KB populated, template created.
 *
 * Frontend slice — verifies that ResumeUpload calls the import API with the
 * dropped/selected file and shows the success badges based on the response.
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import ResumeUpload from "@/components/ResumeUpload"
import { api } from "@/api/client"

vi.mock("@/api/client")

describe("Workflow: Import resume", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("uploads a file via click → shows imported counts and triggers onImported", async () => {
    const onImported = vi.fn()
    vi.mocked(api.importResume).mockResolvedValue({
      experiences: 2, skills: 8, education: 1, projects: 1, duplicates_skipped: 0,
    })

    render(<ResumeUpload onImported={onImported} onViewKnowledge={vi.fn()} />)

    const file = new File(["fake docx bytes"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    })
    const input = document.getElementById("resume-upload") as HTMLInputElement
    await userEvent.upload(input, file)

    await waitFor(() => expect(api.importResume).toHaveBeenCalledWith(file))
    await waitFor(() => expect(screen.getByText(/Resume imported successfully/)).toBeInTheDocument())
    expect(screen.getByText("2 experiences")).toBeInTheDocument()
    expect(screen.getByText("8 skills")).toBeInTheDocument()
    expect(onImported).toHaveBeenCalled()
  })

  it("rejects an unsupported file extension on drop without calling the API", async () => {
    vi.mocked(api.importResume).mockResolvedValue({})

    render(<ResumeUpload onImported={vi.fn()} onViewKnowledge={vi.fn()} />)
    const dropzone = screen.getByText(/Drop your resume here/).closest("div")!.parentElement!

    const badFile = new File(["nope"], "resume.exe", { type: "application/octet-stream" })
    fireEvent.drop(dropzone, { dataTransfer: { files: [badFile] } })

    await waitFor(() => expect(screen.getByText(/Only \.docx, \.pdf, \.txt files are accepted/)).toBeInTheDocument())
    expect(api.importResume).not.toHaveBeenCalled()
  })

  it("surfaces a backend error when the import fails", async () => {
    vi.mocked(api.importResume).mockRejectedValue(new Error("PARSE_FAILED: bad docx"))

    render(<ResumeUpload onImported={vi.fn()} onViewKnowledge={vi.fn()} />)
    const file = new File(["x"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    })
    const input = document.getElementById("resume-upload") as HTMLInputElement
    await userEvent.upload(input, file)

    await waitFor(() => expect(screen.getByText(/PARSE_FAILED/)).toBeInTheDocument())
  })
})
