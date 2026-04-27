import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props { children: ReactNode; name: string }
interface State { error: Error | null; info: ErrorInfo | null }

export default class DebugErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // #region agent log
    const dbg = (window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog
    dbg?.(
      `DebugErrorBoundary[${this.props.name}]`,
      "render error caught",
      {
        hypothesisId: "G",
        boundary: this.props.name,
        message: error.message,
        name: error.name,
        stack: String(error.stack || "").slice(0, 2500),
        componentStack: String(info.componentStack || "").slice(0, 2500),
      }
    )
    // #endregion
    this.setState({ info })
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: "monospace", color: "#b00", whiteSpace: "pre-wrap" }}>
          <h2>UI broke in: {this.props.name}</h2>
          <p><strong>{this.state.error.name}:</strong> {this.state.error.message}</p>
          <details open>
            <summary>component stack</summary>
            <pre>{this.state.info?.componentStack}</pre>
          </details>
          <details>
            <summary>error stack</summary>
            <pre>{this.state.error.stack}</pre>
          </details>
        </div>
      )
    }
    return this.props.children
  }
}
