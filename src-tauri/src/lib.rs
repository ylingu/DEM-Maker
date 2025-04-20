use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            #[cfg(not(debug_assertions))]
            {
                match app.shell().sidecar("backend") {
                    Ok(sidecar_command) => {
                        let _ = sidecar_command.spawn();
                        println!("Backend spawn initiated");
                    }
                    Err(e) => {
                        eprintln!(
                            "Failed to get sidecar command : {}. Check tauri.conf.json.",
                            e
                        );
                    }
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
