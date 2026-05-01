import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const APP_VERSION = "0.1.0"
const IS_TAURI = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window

type UpdateStatus = "idle" | "checking" | "available" | "up-to-date" | "downloading" | "error"

export default function UpdateChecker() {
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>("idle")
  const [updateVersion, setUpdateVersion] = useState("")
  const [errorMessage, setErrorMessage] = useState("")
  const [downloadProgress, setDownloadProgress] = useState(0)

  const checkForUpdates = async () => {
    if (!IS_TAURI) {
      setUpdateStatus("error")
      setErrorMessage("Updates only available in the desktop app. Run 'git pull' to update from source.")
      return
    }

    setUpdateStatus("checking")
    setErrorMessage("")

    try {
      const { check } = await import("@tauri-apps/plugin-updater")
      const update = await check()

      if (update) {
        setUpdateStatus("available")
        setUpdateVersion(update.version)
      } else {
        setUpdateStatus("up-to-date")
      }
    } catch (error) {
      setUpdateStatus("error")
      setErrorMessage(error instanceof Error ? error.message : "Failed to check for updates")
    }
  }

  const installUpdate = async () => {
    if (!IS_TAURI) return

    setUpdateStatus("downloading")
    setDownloadProgress(0)

    try {
      const { check } = await import("@tauri-apps/plugin-updater")
      const update = await check()

      if (!update) return

      await update.downloadAndInstall((event) => {
        if (event.event === "Started" && event.data.contentLength) {
          setDownloadProgress(0)
        } else if (event.event === "Progress") {
          setDownloadProgress(previous => previous + (event.data.chunkLength || 0))
        } else if (event.event === "Finished") {
          setDownloadProgress(100)
        }
      })

      // Restart the app after install
      const { relaunch } = await import("@tauri-apps/plugin-process")
      await relaunch()
    } catch (error) {
      setUpdateStatus("error")
      setErrorMessage(error instanceof Error ? error.message : "Update failed")
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Software Updates</CardTitle>
        <span className="text-xs text-muted-foreground">Current version: {APP_VERSION}</span>
      </CardHeader>
      <CardContent>
        {updateStatus === "idle" && (
          <Button variant="outline" size="sm" onClick={checkForUpdates}>
            Check for Updates
          </Button>
        )}

        {updateStatus === "checking" && (
          <p className="text-sm text-muted-foreground">Checking for updates...</p>
        )}

        {updateStatus === "up-to-date" && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-green-700">You're up to date!</span>
            <Button variant="ghost" size="sm" onClick={() => setUpdateStatus("idle")}>Check again</Button>
          </div>
        )}

        {updateStatus === "available" && (
          <div className="space-y-2">
            <p className="text-sm">
              Version <strong>{updateVersion}</strong> is available.
            </p>
            <div className="flex gap-2">
              <Button size="sm" onClick={installUpdate}>
                Download & Install
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setUpdateStatus("idle")}>
                Later
              </Button>
            </div>
          </div>
        )}

        {updateStatus === "downloading" && (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Downloading update...</p>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-purple-500 rounded-full h-2 transition-all"
                style={{ width: `${Math.min(downloadProgress, 100)}%` }}
              />
            </div>
          </div>
        )}

        {updateStatus === "error" && (
          <div className="space-y-2">
            <p className="text-sm text-destructive">{errorMessage}</p>
            <Button variant="ghost" size="sm" onClick={() => setUpdateStatus("idle")}>Try again</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
