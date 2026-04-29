use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Spawn the Python backend as a sidecar process
      let sidecar = app
        .shell()
        .sidecar("kaarsaaz-backend")
        .expect("failed to create sidecar command");

      let (mut _rx, _child) = sidecar
        .spawn()
        .expect("failed to spawn backend sidecar");

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
