import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import ApartmentCard from "../ApartmentCard"
import type { DashboardListing } from "@/types"

const BASE_LISTING: DashboardListing = {
  id: 1,
  title: "Sunset View Apartment",
  address: "123 Main St, Portland OR",
  source_url: "https://example.com/listing/1",
  image_url: null,
  effective_monthly: 2350,
  match_score: 87,
  stage: "interested",
  photo_count: 5,
  has_intel: false,
}

describe("ApartmentCard", () => {
  it("renders listing title and address", () => {
    render(<ApartmentCard listing={BASE_LISTING} onExpand={() => {}} />)
    expect(screen.getByText("Sunset View Apartment")).toBeInTheDocument()
    expect(screen.getByText("123 Main St, Portland OR")).toBeInTheDocument()
  })

  it("shows effective monthly price in indigo mono font", () => {
    render(<ApartmentCard listing={BASE_LISTING} onExpand={() => {}} />)
    const priceElement = screen.getByText("$2,350/mo")
    expect(priceElement).toBeInTheDocument()
    expect(priceElement.className).toContain("font-mono")
    expect(priceElement.className).toContain("text-indigo-600")
  })

  it("shows score ring with match score", () => {
    render(<ApartmentCard listing={BASE_LISTING} onExpand={() => {}} />)
    // ScoreRing renders the score as text inside the SVG container
    expect(screen.getByText("87")).toBeInTheDocument()
  })

  it("shows stage badge", () => {
    render(<ApartmentCard listing={BASE_LISTING} onExpand={() => {}} />)
    expect(screen.getByText("Interested")).toBeInTheDocument()
  })

  it("shows photo count badge", () => {
    render(<ApartmentCard listing={BASE_LISTING} onExpand={() => {}} />)
    expect(screen.getByText("5 photos")).toBeInTheDocument()
  })

  it("shows singular 'photo' for count of 1", () => {
    const singlePhotoListing = { ...BASE_LISTING, photo_count: 1 }
    render(<ApartmentCard listing={singlePhotoListing} onExpand={() => {}} />)
    expect(screen.getByText("1 photo")).toBeInTheDocument()
  })

  it("calls onExpand when clicked", () => {
    const handleExpand = vi.fn()
    render(<ApartmentCard listing={BASE_LISTING} onExpand={handleExpand} />)
    fireEvent.click(screen.getByRole("button"))
    expect(handleExpand).toHaveBeenCalledTimes(1)
  })

  it("renders placeholder when no image_url", () => {
    render(<ApartmentCard listing={BASE_LISTING} onExpand={() => {}} />)
    // Should render placeholder SVG (house icon), not an img element
    expect(screen.queryByRole("img")).not.toBeInTheDocument()
  })

  it("renders image when image_url is provided", () => {
    const listingWithImage = { ...BASE_LISTING, image_url: "https://example.com/photo.jpg" }
    render(<ApartmentCard listing={listingWithImage} onExpand={() => {}} />)
    const imageElement = screen.getByRole("img")
    expect(imageElement).toBeInTheDocument()
    expect(imageElement).toHaveAttribute("src", "https://example.com/photo.jpg")
  })

  it("renders different stage badge colors correctly", () => {
    const visitedListing = { ...BASE_LISTING, stage: "visited" }
    render(<ApartmentCard listing={visitedListing} onExpand={() => {}} />)
    expect(screen.getByText("Visited")).toBeInTheDocument()
  })

  it("handles missing effective_monthly gracefully", () => {
    const noPriceListing = { ...BASE_LISTING, effective_monthly: null }
    render(<ApartmentCard listing={noPriceListing} onExpand={() => {}} />)
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument()
  })

  it("handles missing match_score gracefully", () => {
    const noScoreListing = { ...BASE_LISTING, match_score: null }
    render(<ApartmentCard listing={noScoreListing} onExpand={() => {}} />)
    // ScoreRing should not render — no score number visible
    expect(screen.queryByText("87")).not.toBeInTheDocument()
  })
})
