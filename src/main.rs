use clap::{Parser, ValueEnum};
use glob::{MatchOptions, Pattern};
use indicatif::{ProgressBar, ProgressIterator, ProgressStyle};
use md5::{Digest, Md5};
use serde::Serialize;
use std::cmp::Ordering;
use std::collections::HashMap;
use std::fs::File;
use std::hash::Hash;
use std::io;
use std::io::{BufReader, Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::process;
use std::str::FromStr;
use std::time::{Duration, Instant};
use walkdir::WalkDir;

type Md5Hash = [u8; 16];

const CHUNK_SIZE: usize = 64 * 1024;
const EMPTY_HASH: &Md5Hash = b"\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~";

enum HashType {
    Full,
    Partial,
}

#[derive(Hash, Eq, PartialEq)]
enum SortKey {
    Size(u64),
    Hash(Md5Hash),
}

#[derive(Clone, Hash)]
struct FileInfo {
    path: PathBuf,
    size: u64,
    hash: Option<Md5Hash>,
}

#[derive(Serialize, Eq, PartialEq)]
struct OutputEntry {
    hash: Option<String>,
    size: Option<u64>,
    paths: Vec<String>,
}

impl Ord for OutputEntry {
    fn cmp(&self, other: &Self) -> Ordering {
        self.size.cmp(&other.size)
    }
}

impl PartialOrd for OutputEntry {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(ValueEnum, Clone)]
enum CompareMethod {
    Size,
    PartialHash,
    Hash,
}

#[derive(ValueEnum, Clone)]
enum OutputFormat {
    Json,
    List,
}

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct CliArgs {
    dirs: Vec<String>,

    #[arg(short, long)]
    exclude: Vec<String>,

    #[arg(short, long)]
    fail_on_duplicate: bool,

    #[arg(short, long, value_enum, default_value_t = CompareMethod::Hash)]
    compare_method: CompareMethod,

    #[arg(short, long, value_enum, default_value_t = OutputFormat::Json)]
    output_format: OutputFormat,
}

fn get_file_paths(dirs: Vec<PathBuf>, exclude: Vec<Pattern>) -> Vec<FileInfo> {
    let mut file_infos = Vec::new();
    let match_options = MatchOptions {
        case_sensitive: !cfg!(windows),
        require_literal_separator: true,
        require_literal_leading_dot: false,
    };
    for dir in dirs {
        for entry in WalkDir::new(dir) {
            if let Err(_e) = entry {
                continue;
            }
            let entry = entry.unwrap();
            let path = entry.path();
            let metadata = path.metadata();
            if let Err(_e) = metadata {
                continue;
            }
            let metadata = metadata.unwrap();
            if path.is_file() {
                if exclude
                    .iter()
                    .any(|pattern| pattern.matches_path_with(path, match_options))
                {
                    continue;
                }
                file_infos.push(FileInfo {
                    path: path.to_owned(),
                    size: metadata.len(),
                    hash: None,
                });
            }
        }
    }
    file_infos
}

fn hash_file(file_info: &FileInfo, hash_type: HashType) -> io::Result<Md5Hash> {
    if file_info.size == 0 {
        return Ok(*EMPTY_HASH);
    }
    if file_info.hash.is_some() && file_info.size <= CHUNK_SIZE as u64 * 3 {
        return Ok(file_info.hash.unwrap());
    }
    let file = File::open(file_info.path.clone())?;
    let mut hasher = Md5::new();
    let mut reader = BufReader::new(file);
    let mut buffer = Vec::new();
    match hash_type {
        HashType::Full => {
            eprintln!("full hash");
            reader.read_to_end(&mut buffer)?;
        }
        HashType::Partial => {
            if file_info.size <= CHUNK_SIZE as u64 * 3 {
                reader.read_to_end(&mut buffer)?;
            } else {
                let mut partial_buffer = [0; CHUNK_SIZE * 3];
                let mut pos = 0;
                pos += reader.read(&mut partial_buffer[pos..CHUNK_SIZE])?;
                reader.seek(SeekFrom::Start(
                    (file_info.size / 2) - (CHUNK_SIZE as u64 / 2),
                ))?;
                pos += reader.read(&mut partial_buffer[pos..CHUNK_SIZE])?;
                reader.seek(SeekFrom::End(-(CHUNK_SIZE as i64)))?;
                pos += reader.read(&mut partial_buffer[pos..CHUNK_SIZE])?;
                buffer.extend_from_slice(&partial_buffer[..pos]);
            }
        }
    }
    hasher.update(&buffer);
    Ok(<Md5Hash>::from(hasher.finalize()))
}

fn main() {
    let args = CliArgs::parse();
    // TODO: ignore errors when validating both paths and patterns
    let dirs = args
        .dirs
        .iter()
        .map(Path::new)
        .map(|path| path.canonicalize().unwrap())
        .collect();
    let exclude = args
        .exclude
        .iter()
        .map(|pattern| Pattern::from_str(pattern).unwrap())
        .collect();
    let compare_method = args.compare_method as isize;
    let progress_style = ProgressStyle::default_bar()
        .template("{msg} {bar:40.green/240} {percent:>3.magenta}% {eta_precise:.cyan} {pos:.green}/{len:.green} {per_sec:.yellow}")
        .unwrap()
        .progress_chars("━╸━");
    let start_time = Instant::now();
    let mut files;
    let mut sorted = HashMap::new();

    // STEP 1: Search for files.
    let bar = ProgressBar::new_spinner()
        .with_style(ProgressStyle::default_spinner().tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"))
        .with_message("Searching for files");
    bar.enable_steady_tick(Duration::from_millis(100));
    files = get_file_paths(dirs, exclude);
    bar.finish_and_clear();
    let total = files.len();
    eprintln!("Found {} files.", total);

    // STEP 2: Check file sizes.
    for file_info in files {
        sorted
            .entry(SortKey::Size(file_info.size))
            .or_insert(Vec::new())
            .push(file_info);
    }
    files = sorted
        .values()
        .filter(|items| items.len() > 1)
        .flat_map(|items| items.clone())
        .collect();
    eprintln!("Found {} files with matching sizes.", files.len());

    // STEP 3: Calculate partial hashes.
    if compare_method >= 1 {
        let bar = ProgressBar::new(files.len() as u64)
            .with_style(progress_style.clone())
            .with_message("Calculating partial hashes");
        files = files
            .into_iter()
            .progress_with(bar)
            .map(|mut file_info| {
                let hash = hash_file(&file_info, HashType::Partial);
                if let Err(err) = hash {
                    eprintln!("Error hashing file: {}", err);
                } else {
                    file_info.hash = Some(hash.unwrap());
                }
                file_info
            })
            .filter(|file_info| file_info.hash.is_some())
            .collect();
        sorted.clear();
        for file_info in files {
            sorted
                .entry(SortKey::Hash(file_info.hash.unwrap()))
                .or_insert(Vec::new())
                .push(file_info);
        }
        files = sorted
            .values()
            .filter(|items| items.len() > 1)
            .flat_map(|items| items.clone())
            .collect();
        eprintln!(
            "Found {} files with partial hashes that match other files.",
            files.len()
        );
    }

    // STEP 4: Calculate full hashes.
    if compare_method >= 2 {
        let bar = ProgressBar::new(files.len() as u64)
            .with_style(progress_style.clone())
            .with_message("Calculating full hashes");
        files = files
            .into_iter()
            .progress_with(bar)
            .map(|mut file_info| {
                let hash = hash_file(&file_info, HashType::Full);
                if let Err(err) = hash {
                    eprintln!("Error hashing file: {}", err);
                } else {
                    file_info.hash = Some(hash.unwrap());
                }
                file_info
            })
            .filter(|file_info| file_info.hash.is_some())
            .collect();
        sorted.clear();
        for file_info in files {
            sorted
                .entry(SortKey::Hash(file_info.hash.unwrap()))
                .or_insert(Vec::new())
                .push(file_info);
        }
        files = sorted
            .values()
            .filter(|items| items.len() > 1)
            .flat_map(|items| items.clone())
            .collect();
        eprintln!(
            "Found {} files with hashes that match other files.", // FIXME: what is going on here? same results as partial hash...
            files.len()
        );
    }
    eprintln!(
        "Found {} duplicate files in {:.4} seconds ({:.2}% of all files).",
        files.len(),
        start_time.elapsed().as_secs_f32(),
        files.len() as f32 / total as f32 * 100.0,
    );

    // STEP 5: Output results.
    let mut output = Vec::new();
    for (key, file_infos) in sorted {
        if file_infos.len() > 1 {
            let obj = OutputEntry {
                hash: match key {
                    SortKey::Hash(hash) => Some(hash.map(|byte| format!("{:x}", byte)).concat()),
                    SortKey::Size(_) => None,
                },
                size: file_infos.first().map(|file_info| file_info.size),
                paths: file_infos
                    .into_iter()
                    .map(|file_info| file_info.path.to_str().unwrap().to_owned())
                    .collect(),
            };
            output.push(obj);
        }
    }
    output.sort_unstable();
    match args.output_format {
        OutputFormat::Json => {
            println!("{}", serde_json::to_string_pretty(&output).unwrap());
        }
        OutputFormat::List => {
            for entry in output {
                if let Some(hash) = entry.hash {
                    println!("\n{}", hash);
                } else if let Some(size) = entry.size {
                    println!("\n{}", size);
                } else {
                    continue;
                }
                for path in entry.paths {
                    println!("  {}", path);
                }
            }
        }
    }
    process::exit(args.fail_on_duplicate as i32)
}
