import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import VisitPhotoGallery from "../VisitPhotoGallery"
import type { VisitPhoto } from "@/types"

// Mock the API client
vi.mock("@/api/client", () => ({
  api: {
    getPhotos: vi.fn(),
    savePhotos: vi.fn(),
    updatePhoto: vi.fn(),
    deletePhoto: vi.fn(),
    analyzePhotos: vi.fn(),
  },
}))

import { api } from "@/api/client"

const MOCK_PHOTOS: VisitPhoto[] = [
  {
    id: 1,
    listing_id: 42,
    file_path: "photos/42/aaa-bbb-ccc.jpg",
    label: "Kitchen view",
    room_tag: "kitchen",
    display_order: 0,
    ai_analysis: null,
    created_at: "2026-05-01T12:00:00Z",
  },
  {
    id: 2,
    listing_id: 42,
    file_path: "photos/42/ddd-eee-fff.jpg",
    label: "Bedroom window",
    room_tag: "bedroom",
    display_order: 1,
    ai_analysis: null,
    created_at: "2026-05-01T12:01:00Z",
  },
]

describe("VisitPhotoGallery", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders empty state when no photos exist", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue([])

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText(/no visit photos yet/i)).toBeInTheDocument()
    })
  })

  it("renders photo grid with labels when photos exist", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue(MOCK_PHOTOS)

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText("Kitchen view")).toBeInTheDocument()
      expect(screen.getByText("Bedroom window")).toBeInTheDocument()
    })
  })

  it("renders room tag overlays on photos", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue(MOCK_PHOTOS)

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText("kitchen")).toBeInTheDocument()
      expect(screen.getByText("bedroom")).toBeInTheDocument()
    })
  })

  it("shows upload button", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue([])

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText("Upload Photos")).toBeInTheDocument()
    })
  })

  it("shows analyze button when photos exist", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue(MOCK_PHOTOS)

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText("Analyze My Photos")).toBeInTheDocument()
    })
  })

  it("does not show analyze button in empty state", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue([])

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText(/no visit photos yet/i)).toBeInTheDocument()
    })
    expect(screen.queryByText("Analyze My Photos")).not.toBeInTheDocument()
  })

  it("upload button triggers hidden file input", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue([])

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      expect(screen.getByText("Upload Photos")).toBeInTheDocument()
    })

    // The upload label should be associated with a hidden file input
    const uploadLabel = screen.getByText("Upload Photos")
    const inputId = uploadLabel.getAttribute("for")
    expect(inputId).toBe("photo-upload-42")

    const fileInput = document.getElementById(inputId!) as HTMLInputElement
    expect(fileInput).toBeInTheDocument()
    expect(fileInput.type).toBe("file")
    expect(fileInput.accept).toBe("image/*")
  })

  it("renders delete button on each photo", async () => {
    vi.mocked(api.getPhotos).mockResolvedValue(MOCK_PHOTOS)

    render(<VisitPhotoGallery listingId={42} />)

    await waitFor(() => {
      const deleteButtons = screen.getAllByTitle("Delete photo")
      expect(deleteButtons).toHaveLength(2)
    })
  })

  it("shows loading skeleton initially", () => {
    vi.mocked(api.getPhotos).mockReturnValue(new Promise(() => {})) // never resolves

    render(<VisitPhotoGallery listingId={42} />)

    // Should show the animate-pulse skeleton
    const skeleton = document.querySelector(".animate-pulse")
    expect(skeleton).toBeInTheDocument()
  })
})
