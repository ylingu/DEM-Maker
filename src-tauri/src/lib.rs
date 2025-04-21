use command_group::{CommandGroup, GroupChild};
use std::process::Command;
use std::sync::{Arc, Mutex};
use tauri::{Manager, State, WindowEvent};

struct ManagedChildProcess(Arc<Mutex<Option<GroupChild>>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_log::Builder::new()
                .target(tauri_plugin_log::Target::new(
                    tauri_plugin_log::TargetKind::LogDir {
                        file_name: Some("logs".to_string()),
                    },
                ))
                .build(),
        )
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            #[cfg(not(debug_assertions))]
            {
                let process = Command::new("backend")
                    .group_spawn()
                    .expect("Failed to spawn process");
                app.manage(ManagedChildProcess(Arc::new(Mutex::new(Some(process)))));
            }
            Ok(())
        })
        .on_window_event(|app_handle, event| {
            match event {
                WindowEvent::CloseRequested { api, .. } => {
                    #[cfg(not(debug_assertions))]
                    {
                        println!("Window close requested. Attempting to kill sidecar...");
                        api.prevent_close(); // Prevent the window from closing immediately
                        let state: State<ManagedChildProcess> = app_handle.state();
                        let mut child_lock = state.inner().0.lock().unwrap();
                        let mut child_process = child_lock.take().unwrap();
                        child_process
                            .kill()
                            .expect("Failed to kill sidecar process");
                        app_handle.app_handle().exit(0);
                    }
                }
                _ => {}
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
