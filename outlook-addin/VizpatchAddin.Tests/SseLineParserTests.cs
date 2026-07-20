using VizpatchAddin.Core;
using Xunit;

namespace VizpatchAddin.Tests
{
    public class SseLineParserTests
    {
        [Fact]
        public void TextChunk_SingleDataLine_YieldsMessageFrame()
        {
            var p = new SseLineParser();
            Assert.Null(p.Feed("data: Hallo"));
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("message", frame.Value.EventType);
            Assert.Equal("Hallo", frame.Value.Data);
        }

        [Fact]
        public void TextChunk_MultipleDataLines_JoinedWithNewline()
        {
            var p = new SseLineParser();
            Assert.Null(p.Feed("data: Zeile eins"));
            Assert.Null(p.Feed("data: Zeile zwei"));
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("message", frame.Value.EventType);
            Assert.Equal("Zeile eins\nZeile zwei", frame.Value.Data);
        }

        [Fact]
        public void ToolEvent_YieldsToolFrameWithLabel()
        {
            var p = new SseLineParser();
            Assert.Null(p.Feed("event: tool"));
            Assert.Null(p.Feed("data: mails_suchen"));
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("tool", frame.Value.EventType);
            Assert.Equal("mails_suchen", frame.Value.Data);
        }

        [Fact]
        public void DoneEvent_YieldsDoneFrameWithEmptyData()
        {
            // Server sendet: "event: done\ndata: \n\n"
            var p = new SseLineParser();
            Assert.Null(p.Feed("event: done"));
            Assert.Null(p.Feed("data: "));
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("done", frame.Value.EventType);
            Assert.Equal("", frame.Value.Data);
        }

        [Fact]
        public void ErrorEvent_YieldsErrorFrameWithMessage()
        {
            var p = new SseLineParser();
            Assert.Null(p.Feed("event: error"));
            Assert.Null(p.Feed("data: Interner Fehler bei der Verarbeitung."));
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("error", frame.Value.EventType);
            Assert.Equal("Interner Fehler bei der Verarbeitung.", frame.Value.Data);
        }

        [Theory]
        [InlineData("data:   dreifach", "dreifach")] // TrimStart entfernt ALLE fuehrenden Leerzeichen
        [InlineData("data: eins", "eins")]
        public void DataPrefix_TrimStartRemovesLeadingSpaces(string line, string expected)
        {
            var p = new SseLineParser();
            p.Feed(line);
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal(expected, frame.Value.Data);
        }

        [Fact]
        public void EventPrefix_TrimStartRemovesLeadingSpace()
        {
            var p = new SseLineParser();
            p.Feed("event:   tool");
            p.Feed("data: x");
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("tool", frame.Value.EventType);
        }

        [Fact]
        public void BlankLineWithoutContent_YieldsNothing()
        {
            var p = new SseLineParser();
            Assert.Null(p.Feed(""));
            Assert.Null(p.Feed(""));
        }

        [Fact]
        public void OtherFields_id_retry_AreIgnored()
        {
            var p = new SseLineParser();
            Assert.Null(p.Feed("id: 42"));
            Assert.Null(p.Feed("retry: 1000"));
            Assert.Null(p.Feed("data: text"));
            var frame = p.Feed("");
            Assert.NotNull(frame);
            Assert.Equal("message", frame.Value.EventType);
            Assert.Equal("text", frame.Value.Data);
        }
    }
}
