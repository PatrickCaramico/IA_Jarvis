package com.patrick.jarvis;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;

/**
 * V6.5.9: entrega o APK baixado ao instalador padrão do Android (content://com.patrick.jarvis.apk/update.apk).
 * Em celulares Xiaomi/HyperOS a instalação "por sessão" travava em 100%; abrir o instalador do sistema
 * com o arquivo funciona em qualquer Android. Só leitura, só esse arquivo, só para quem recebeu a permissão.
 */
public class ApkProvider extends ContentProvider {
    static final String AUTHORITY = "com.patrick.jarvis.apk";
    static final String NAME = "update.apk";

    static Uri uri() {
        return Uri.parse("content://" + AUTHORITY + "/" + NAME);
    }

    private File file() {
        return new File(getContext().getCacheDir(), "jarvis-update.apk");
    }

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!NAME.equals(uri.getLastPathSegment()) || !"r".equals(mode)) throw new FileNotFoundException();
        return ParcelFileDescriptor.open(file(), ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override
    public String getType(Uri uri) {
        return "application/vnd.android.package-archive";
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] args, String sort) {
        MatrixCursor c = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
        c.addRow(new Object[]{"JARVIS.apk", file().length()});
        return c;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] args) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] args) {
        return 0;
    }
}
