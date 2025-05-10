#[cfg(not(debug_assertions))]
use command_group::{CommandGroup, GroupChild};
#[cfg(not(debug_assertions))]
use std::process::Command;
#[cfg(not(debug_assertions))]
use std::sync::{Arc, Mutex}; 
#[cfg(not(debug_assertions))]
use tauri::{Manager, State};
use tauri::WindowEvent; 

#[cfg(not(debug_assertions))]
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
            #[cfg(debug_assertions)]
            let _ = app; 

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
            #[cfg(debug_assertions)]
            let _ = app_handle; 

            match event {
                WindowEvent::CloseRequested { api, .. } => {
                    #[cfg(debug_assertions)]
                    let _ = api;

                    #[cfg(not(debug_assertions))]
                    {
                        println!("Window close requested. Attempting to kill sidecar...");
                        api.prevent_close(); 
                        let state: State<ManagedChildProcess> = app_handle.state();
                        let mut child_lock = state.inner().0.lock().unwrap();
                        if let Some(mut child_process) = child_lock.take() {
                            child_process
                                .kill()
                                .expect("Failed to kill sidecar process");
                            println!("Sidecar process killed successfully.");
                        } else {
                            println!("Sidecar process was already None or taken.");
                        }
                        app_handle.app_handle().exit(0);
                    }
                }
                _ => {}
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
