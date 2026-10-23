on run argv
  set folderPath to item 1 of argv
  set albumName to item 2 of argv
  set imgFolder to POSIX file folderPath
  tell application "Finder"
    set theFiles to (every file of folder imgFolder whose name extension is "png") as alias list
  end tell
  tell application "Photos"
    if not (exists album albumName) then
      make new album named albumName
    end if
    set targetAlbum to album albumName
    import theFiles into targetAlbum skip check duplicates yes
  end tell
  return "imported " & (count of theFiles) & " into " & albumName
end run
